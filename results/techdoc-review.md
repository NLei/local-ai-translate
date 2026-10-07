# PASSAGE 1 原文

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



## Hy-MT2-1.8B

## PCI 驱动程序的结构

PCI 驱动程序通过 `pci_register_driver()` 在系统中“发现” PCI 设备。
实际上，情况恰恰相反。当 PCI 通用代码发现新设备时，具有匹配“描述”的驱动程序将收到通知。
详情如下。

`pci_register_driver()` 将设备的探测工作大部分交给 PCI 层，并支持设备的在线插入/移除[因此支持热插拔 PCI、CardBus 和 Express-Card 在单个驱动程序中]。
`pci_register_driver()` 调用需要传入函数指针表，从而决定了驱动程序的高层次结构。

一旦驱动程序知道有 PCI 设备并且拥有其所有权，通常需要进行以下初始化操作：

- 启用设备
- 请求 MMIO/IOP 资源
- 设置 DMA 掩码大小（适用于相干和流式 DMA）
- 分配并初始化共享控制数据（`pci_allocate_coherent()`）
- 访问设备配置空间（如需要）
- 注册 IRQ 处理程序（`request_irq()`）
- 初始化芯片的非 PCI 部分（即 LAN/SCSI 等）
- 启用 DMA/处理引擎

当使用设备完成后，如果模块需要卸载，驱动程序需要执行以下步骤：

- 禁用设备生成 IRQs 的功能
- 释放 IRQ（`free_irq()`）
- 停止所有 DMA 活动
- 释放 DMA 缓冲区（包括流式和相干）
- 从其他子系统（如 scsi 或 netdev）中注销
- 释放 MMIO/IOP 资源
- 禁用设备

如果 PCI 子系统未配置（`CONFIG_PCI` 未设置），下面描述的大多数 PCI 函数被定义为内联函数，要么完全为空，要么只返回适当的错误代码，以避免驱动程序中出现大量 ifdef 语句。

---

## Qwen3.5-0.8B

## PCI 驱动结构

PCI 驱动通过 `pci_register_driver()` 发现并注册 PCI 设备。实际上，相反的操作：当 PCI 通用代码发现新设备时，与该描述相匹配的驱动程序会被通知。

关于此细节，下文介绍。

`pci_register_driver()` 将大多数探测工作交给 PCI 层，支持在线插入/移除设备 [从而支持热插拔 PCI、CardBus 和 Express-Card 设备，由一个驱动完成]。

`pci_register_driver()` 调用需要传入函数指针表，因此决定了驱动程序的高层结构。

一旦驱动程序知道 PCI 设备并将其占有了控制权，驱动程序通常需要进行以下初始化：

- 启用设备
- 请求 MMIO/IOP 资源
- 设置 DMA 掩码大小（对于既含协同也含流式 DMA）
- 分配并初始化共享控制数据（`pci_allocate_coherent()`）
- 访问设备配置空间（如需要）
- 注册 IRQ 处理程序（`request_irq()`）
- 初始化非 PCI 部分（如 LAN/SCSI 等）
- 启用 DMA/处理引擎

当使用设备完成之后，如果模块需要卸载，驱动程序则需要进行以下步骤：

- 从 IRQ 中禁用设备
- 释放 IRQ（`free_irq()`）
- 停止所有 DMA 活动
- 释放 DMA 缓冲区（既含流式也含协同）
- 从其他子系统（如 SCSI 或 netdev）卸载
- 释放 MMIO/IOP 资源
- 禁用设备

如果 PCI 子系统未配置（`CONFIG_PCI` 未设置），则以下大多数 PCI 函数定义为内联函数，完全为空或仅返回适当的错误码，以避免驱动程序中大量的 `ifdefs`。

---

## Qwen3-0.6B

PCI驱动结构

PCI驱动"discover"通过调用`pci_register_driver()`发现PCI设备。实际上，这是反向的过程。当PCI通用代码发现新的设备时，匹配“描述”的驱动将被通知。以下是对这一机制的说明。

`pci_register_driver()`将大部分设备的探测任务交给PCI层，并支持在线插入/删除设备，从而支持在单个驱动中实现热插拔、卡串和表达卡。该调用需要传递一个指向函数指针的表，因此决定了驱动的高层结构。

一旦驱动知道设备并取得所有权，通常需要执行以下初始化：

- 启用设备
- 请求MMIO/IOP资源
- 设置DMA掩码大小（用于对称和流式DMA）
- 为共享控制数据分配并初始化（使用`pci_allocate_coherent()`）
- 如果需要，访问设备配置空间
- 注册IRQ处理函数（使用`request_irq()`）
- 初始化非PCI部分（例如LAN、SCSI等）的芯片部分
- 开启DMA/处理引擎

完成使用设备后，如果模块需要卸载，驱动需要执行以下步骤：

- 关闭设备生成IRQ的设置
- 释放IRQ（使用`free_irq()`）
- 停止所有DMA活动
- 关闭DMA缓冲区（包括流式和对称）
- 解除其他子系统（例如SCSI或网络设备）的注册
- 关闭MMIO/IOP资源
- 关闭设备

如果PCI子系统未配置（`CONFIG_PCI`未启用），以下描述中的大部分PCI功能通常被定义为内联函数，要么完全为空，要么返回适当的错误代码，以避免驱动中大量if语句。

---

# PASSAGE 2 原文


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



## Hy-MT2-1.8B

## 启用 PCI 设备

在访问任何设备寄存器之前，驱动程序需要通过调用 `pci_enable_device()` 来启用 PCI 设备。这将：

- 如果设备处于暂停状态，则唤醒该设备；
- 分配设备的 I/O 和内存区域（如果 BIOS 未分配）；
- 分配 IRQ（如果 BIOS 未分配）。

> **注意**
> `pci_enable_device()` 可能会失败！请检查返回值。

> **警告**
> 操作系统错误：我们在启用这些资源之前不检查资源分配。如果在调用 `pci_enable_device()` 之前调用 `pci_request_resources()`，顺序会更合理。目前，当两个设备被分配到同一范围时，设备驱动程序无法检测此错误。这不是常见问题，且不太可能很快得到修复。

`pci_set_master()` 通过设置 PCI_COMMAND 寄存器中的总线主设备位来启用 DMA，如果 BIOS 设置的延迟计时值不合理，也会进行修正。`pci_clear_master()` 通过清除总线主设备位来禁用 DMA。

如果 PCI 设备可以使用 PCI Memory-Write-Invalidate 操作，请调用 `pci_set_mwi()`。这会启用 PCI_COMMAND 中的 Mem-Wr-Inval 位，并确保缓存行大小寄存器设置正确。请注意，`pci_set_mwi()` 的返回值，因为并非所有架构或芯片组都支持 Memory-Write-Invalidate。或者，如果 Mem-Wr-Inval 是需要的但不是必需的，可以调用 `pci_try_set_mwi()`，让系统尽力启用 Mem-Wr-Inval。

---

## Qwen3.5-0.8B

## Enable the PCI device

在接触任何设备寄存器之前，驱动程序必须通过调用 `pci_enable_device()` 使 PCI 设备启用。此操作将：

- 唤醒设备（若设备处于休眠状态）
- 分配设备的 I/O 和内存区域（若 BIOS 未分配）
- 分配 IRQ（若 BIOS 未分配）

> **注意**  
> `pci_enable_device()` 可能失败！请检查返回值。

> **警告**  
> OS BUG: 在启用资源前，我们未检查资源分配。若按此顺序调用 `pci_enable_device()`，将更合理。  
> 当前情况下，设备驱动无法检测两个设备共享相同范围资源的问题。这是一个罕见问题，且短期内难以修复。

`pci_set_master()` 通过将 PCI 命令寄存器中的总线 Master 位设置为 DMA 模式，启用 DMA；同时若 BIOS 设置的定时器值异常，也会修复该问题。`pci_clear_master()` 将禁用 DMA，通过清除总线 Master 位来实现。

若 PCI 设备支持 PCI 内存写入无效（PCI-MWI）事务，则调用 `pci_set_mwi()`。此操作使 PCI 命令寄存器中的内存写入无效位有效，并正确设置缓存行大小寄存器。检查 `pci_set_mwi()` 的返回值：并非所有架构或芯片组均支持 PCI-MWI。若 Mem-Wr-Inval 在理想情况下很有用，但并非必需，可调用 `pci_try_set_mwi()` 让系统尽力启用 Mem-Wr-Inval。

---

## Qwen3-0.6B

## 启用PCI设备

在接触任何设备寄存器之前，驱动程序必须通过调用`pci_enable_device()`启用PCI设备。这包括：

- 如果设备处于休眠状态，唤醒设备；
- 如果BIOS未分配设备的I/O和内存区域，则分配这些区域；
- 如果BIOS未分配设备的中断（IRQ），则分配IRQ。

> **提示**
> `pci_enable_device()`可能失败！请检查返回值。

> **警告**
> 我们没有在启用这些资源之前检查资源分配。如果资源分配顺序是先调用`pci_request_resources()`再调用`pci_enable_device()`，这将更合理。目前，设备驱动程序不能在两个设备共享同一范围分配资源时检测到此BUG。这并非常见问题，且不太可能在未来得到修复。

`pci_set_master()`将通过设置PCI命令寄存器中的“DMA”位启用DMA。如果BIOS设置的延迟时间值为无效值，则会修复该问题。`pci_clear_master()`将通过清除“DMA”位清除DMA。

如果PCI设备可以使用PCI内存写入无效（Mem-Wr-Inval）事务，则调用`pci_set_mwi()`。这将为Mem-Wr-Inval位设置PCI命令位，并确保缓存线长度寄存器正确设置。请检查`pci_set_mwi()`的返回值，以确认是否所有架构或芯片集都支持内存写入无效。如果Mem-Wr-Inval是希望的但不必要，调用`pci_try_set_mwi()`，以尽可能地启用Mem-Wr-Inval。

---

# PASSAGE 3 原文


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


## Hy-MT2-1.8B

## MMIO 空间与“写发布”机制

将驱动程序从使用 I/O 端口空间转换为使用 MMIO 空间时，通常需要进行一些额外的修改。特别是需要处理“写发布”机制。许多驱动程序（例如 tg3、acenic、sym53c8xx_2）已经实现了这一机制。I/O 端口空间确保写入操作在 CPU 能够继续之前就能到达 PCI 设备。而写入 MMIO 空间则允许 CPU 在操作到达 PCI 设备之前继续工作。硬件工程师将这称为“写发布”，因为写入完成会在操作到达目标之前被“发布”给 CPU。

因此，对时序敏感的代码应在 CPU 预期等待的地方添加 `readl()` 指令，以便进行其他操作。对于 I/O 端口空间，经典的“位操作”序列即可生效：

```c
for (i = 8; --i; val >>= 1) {
        outb(val & 1, ioport_reg);      /* 写入位 */
        udelay(10);
}
```

对于 MMIO 空间，相同的序列应为：

```c
for (i = 8; --i; val >>= 1) {
        writeb(val & 1, mmio_reg);      /* 写入位 */
        readb(safe_mmio_reg);           /* 刷新已发布的写入数据 */
        udelay(10);
}
```

重要的是，“safe_mmio_reg”不应有任何会干扰设备正确操作的副作用。

另一个需要注意的情况是在重置 PCI 设备时。应使用 PCI 配置空间的读取来刷新 `writel()`。如果预期 PCI 设备在 `readl()` 时不会响应，则会在所有平台上优雅地处理 PCI 主机的中断。大多数 x86 平台允许 MMIO 读取导致主机中断（即“软失败”），并返回无效数据（例如 ~0）。但许多 RISC 平台会崩溃（即“硬失败”）。

---

## Qwen3.5-0.8B

## MMIO Space and "Write Posting"

将驱动程序从使用 I/O 端口空间转换为使用 MMIO 空间通常需要一些额外的更改。具体来说，需要处理“写后”（write posting）。许多驱动程序（例如 tg3、acenic 和 sym53c8xx_2）已经实现了这一点。I/O 端口空间保证写交易在到达 PCI 设备之前完成，而 CPU 在 PCI 设备之后才能继续。在 MMIO 空间中执行写操作允许 CPU 在 PCI 设备之前继续。由于写完成是“发布”（posted）给 CPU 而非写入目标，因此将这一特性称为“写后”。

因此，时序敏感的代码应在 CPU 期望在继续之前进行 `readl()` 操作，以等待。经典的“位乱序”（bit banging）序列在 I/O 端口空间可用：

```c
for (i = 8; --i; val >>= 1) {
    outb(val & 1, ioport_reg);      /* 写位 */
    udelay(10);
}
```

对于 MMIO 空间，该序列应为：

```c
for (i = 8; --i; val >>= 1) {
    writeb(val & 1, mmio_reg);      /* 写位 */
    readb(safe_mmio_reg);           /* 发布已发布写 */
    udelay(10);
}
```

重要的是，`safe_mmio_reg` 不应有副作用，这些副作用将干扰设备的正确操作。

此外，需要特别注意当重置 PCI 设备时。使用 PCI 配置空间读取来发布 `writel()`。这将优雅地处理 PCI 主从所有平台上的 PCI 设备在期望不响应 `readl()` 时的 PCI 主中断。大多数 x86 平台允许 MMIO 读取作为主中断（也称为“软失败”）。但是，许多 RISC 平台会崩溃（也称为“硬失败”）。

---

## Qwen3-0.6B

## MMIO空间与“写入提交”

将驱动从使用I/O端口空间转换为使用MMIO空间，通常需要做一些额外的修改。具体来说，“写入提交”需要处理。许多驱动（例如tg3、acenic、sym53c8xx_2）已经实现了这一功能。I/O端口空间保证了写入操作在CPU准备好继续执行之前到达PCI设备。写入MMIO空间可以让CPU在交易到达PCI设备之前继续执行。我们称之为“写入提交”的硬件单元，因为写入完成“被提交”到CPU之前，交易已经到达其目的地。

因此，对具有较高时序要求的代码，应添加readl()函数，其中CPU预期等待前执行其他工作。经典的“位震荡”序列在I/O端口空间上工作良好：

```c
for (i = 8; --i; val >>= 1) {
        outb(val & 1, ioport_reg);      /* 写入位 */
        udelay(10);
}
```

对于MMIO空间，应使用以下序列：

```c
for (i = 8; --i; val >>= 1) {
        writeb(val & 1, mmio_reg);      /* 写入位 */
        readb(safe_mmio_reg);           /* 释放已提交的写入 */
        udelay(10);
}
```

重要的是，确保“safe_mmio_reg”不产生任何干扰设备正常工作的副作用。另一个需要特别注意的案例是当PCI设备被重置时。使用PCI配置空间读取`writel()`来清除该操作，这将优雅地处理PCI设备的主中断。如果PCI设备预期不会调用`readl()`，则大多数x86平台将允许MMIO读取主中断（即“软失败”），并返回垃圾值（例如~0）。然而，许多RISC平台将导致错误（即“硬失败”）。

---

