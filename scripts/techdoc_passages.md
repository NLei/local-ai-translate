===== PASSAGE 1 =====
## Structure of PCI drivers

PCI drivers "discover" PCI devices in a system via `pci_register_driver()`.
Actually, it's the other way around. When the PCI generic code discovers
a new device, the driver with a matching "description" will be notified.
Details on this below.

`pci_register_driver()` leaves most of the probing for devices to
the PCI layer and supports online insertion/removal of devices [thus
supporting hot-pluggable PCI, CardBus, and Express-Card in a single driver].
The `pci_register_driver()` call requires passing in a table of function
pointers and thus dictates the high level structure of a driver.

Once the driver knows about a PCI device and takes ownership, the
driver generally needs to perform the following initialization:

- Enable the device
- Request MMIO/IOP resources
- Set the DMA mask size (for both coherent and streaming DMA)
- Allocate and initialize shared control data (`pci_allocate_coherent()`)
- Access device configuration space (if needed)
- Register IRQ handler (`request_irq()`)
- Initialize non-PCI (i.e. LAN/SCSI/etc) parts of the chip
- Enable DMA/processing engines

When done using the device, and perhaps the module needs to be unloaded,
the driver needs to take the following steps:

- Disable the device from generating IRQs
- Release the IRQ (`free_irq()`)
- Stop all DMA activity
- Release DMA buffers (both streaming and coherent)
- Unregister from other subsystems (e.g. scsi or netdev)
- Release MMIO/IOP resources
- Disable the device

If the PCI subsystem is not configured (`CONFIG_PCI` is not set), most of
the PCI functions described below are defined as inline functions either
completely empty or just returning an appropriate error code to avoid
lots of ifdefs in the drivers.

===== PASSAGE 2 =====

## Enable the PCI device

Before touching any device registers, the driver needs to enable
the PCI device by calling `pci_enable_device()`. This will:

- wake up the device if it was in suspended state,
- allocate I/O and memory regions of the device (if BIOS did not),
- allocate an IRQ (if BIOS did not).

> **note**
> `pci_enable_device()` can fail! Check the return value.

> **warning**
> OS BUG: we don't check resource allocations before enabling those
> resources. The sequence would make more sense if we called
> `pci_request_resources()` before calling `pci_enable_device()`.
> Currently, the device drivers can't detect the bug when two
> devices have been allocated the same range. This is not a common
> problem and unlikely to get fixed soon.

`pci_set_master()` will enable DMA by setting the bus master bit
in the PCI_COMMAND register. It also fixes the latency timer value if
it's set to something bogus by the BIOS. `pci_clear_master()` will
disable DMA by clearing the bus master bit.

If the PCI device can use the PCI Memory-Write-Invalidate transaction,
call `pci_set_mwi()`. This enables the PCI_COMMAND bit for Mem-Wr-Inval
and also ensures that the cache line size register is set correctly.
Check the return value of `pci_set_mwi()` as not all architectures
or chip-sets may support Memory-Write-Invalidate. Alternatively,
if Mem-Wr-Inval would be nice to have but is not required, call
`pci_try_set_mwi()` to have the system do its best effort at enabling
Mem-Wr-Inval.

===== PASSAGE 3 =====

## MMIO Space and "Write Posting"

Converting a driver from using I/O Port space to using MMIO space
often requires some additional changes. Specifically, "write posting"
needs to be handled. Many drivers (e.g. tg3, acenic, sym53c8xx_2)
already do this. I/O Port space guarantees write transactions reach the PCI
device before the CPU can continue. Writes to MMIO space allow the CPU
to continue before the transaction reaches the PCI device. HW weenies
call this "Write Posting" because the write completion is "posted" to
the CPU before the transaction has reached its destination.

Thus, timing sensitive code should add `readl()` where the CPU is
expected to wait before doing other work. The classic "bit banging"
sequence works fine for I/O Port space:

```c
for (i = 8; --i; val >>= 1) {
        outb(val & 1, ioport_reg);      /* write bit */
        udelay(10);
}
```

The same sequence for MMIO space should be:

```c
for (i = 8; --i; val >>= 1) {
        writeb(val & 1, mmio_reg);      /* write bit */
        readb(safe_mmio_reg);           /* flush posted write */
        udelay(10);
}
```

It is important that "safe_mmio_reg" not have any side effects that
interferes with the correct operation of the device.

Another case to watch out for is when resetting a PCI device. Use PCI
Configuration space reads to flush the `writel()`. This will gracefully
handle the PCI master abort on all platforms if the PCI device is
expected to not respond to a `readl()`. Most x86 platforms will allow
MMIO reads to master abort (a.k.a. "Soft Fail") and return garbage
(e.g. ~0). But many RISC platforms will crash (a.k.a. "Hard Fail").
