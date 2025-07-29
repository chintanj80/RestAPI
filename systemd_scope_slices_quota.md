# Managing CPU and Memory on RHEL Linux

### Limit CPU usage on a Linux System

Use systemd slice to limit the CPU usage for a process

Sample config of a  systemd slice File

Location = /etc/systemd/system

Filename = slice400.slice  # 400 is to limit to 400% of CPU which is 4 CPU cores, 100% is 1 cpu core

```bash
cd /etc/systemd/system
vi slice400.slice
```

slice400.slice

```systemd
[Unit]
Description=Limit Processes attached to this slice to 4 CPU Cores

[Slice]
CPUQuota=400%


```



Sample service to use up to 8 cpu cores at 100%

cpuhog.service

```systemd
[Unit]
Description=Sample CPU hog Service

[Service]
ExecStart=/usr/bin/stress --cpu 8
```

```bash
systemctl daemon-reload
systemctl start cpuhog
```

Limiting cpuhog service to 400%

```systemd
```systemd
[Unit]
Description=Sample CPU hog Service

[Service]
Slice=slice400.slice
ExecStart=/usr/bin/stress --cpu 8
```
```

Setting cpu affinity for a systemd slice

Below slice is set to use only CPU cores 0 thru 3, 4 cores in total

slice400.slice

```systemd
[Unit]
Description=Limit Processes attached to this slice to 4 CPU Cores

[Slice]
CPUQuota=400%
AllowedCPUs=0-3
```

Splitting the slice into child slice with variable percentage of resources

Create two child slices for the slice400.slice with 75% and 25% of the quota

slice400-child25.slice

```systemd
```systemd
[Unit]
Description=Use 25% of the available cores for parent slice

[Slice]
CPUQuota=400%
```
```

### Start a process with limited CPU Quota using systemd-run scope

```shell
sudo systemd-run --scope -p CPUQuota=50% -- stress --cpu 4
```

CPUQuota = Percent of CPU allocated to the Process

100% = 1 entire CPU

We have asked stress command to run this process on 4 cpus

stress is a linux tool that allows you to simulate cpu usage like a real world process. It can be controlled via parameters

As we ask stress to distribute the load across 4 CPUs but systemd-scope has limited the available resources to this process to the equivalent of 50% cpu. This 50% gets divided across 4 CPU's. This results in each CPU getting utilized only 12.5 %.




