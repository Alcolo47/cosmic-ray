import time


def _read_stat():
    with open('/proc/stat') as f:
        for line in f:
            if line.startswith('cpu '):
                vals = line.split()
                vals13 = int(vals[1]) + int(vals[3])
                return vals13, int(vals[4])


def get_cpu_usage():
    """like psutil.get_cpu_usage without psutil (psutil is not compatible with mitogen)
    """
    a1, b1 = get_cpu_usage.last
    a2, b2 = _read_stat()
    get_cpu_usage.last = (a2, b2)
    if a1 is None:
        time.sleep(2)
        return get_cpu_usage()
    return (a2 - a1) / (a2 + b2 - a1 - b1)


get_cpu_usage.last = (None, None)


def _read_time_in_queue_disk_stat(filename):
    with open(filename) as f:
        for line in f:
            return int(line.split()[10])


def get_disk_time_in_queue():
    files = get_disk_time_in_queue.files

    if files is None:
        import glob
        files = glob.glob('/sys/block/sd*/stat')
        get_disk_time_in_queue.files = files
        last_tiq, last_time = None, None
    else:
        last_tiq, last_time = get_disk_time_in_queue.last

    tiq = sum(_read_time_in_queue_disk_stat(f) for f in files)
    tim = time.time()
    get_disk_time_in_queue.last = (tiq, tim)

    if last_tiq is None:
        time.sleep(1)
        return get_disk_time_in_queue()

    return (tiq - last_tiq) / (tim / last_time)


get_disk_time_in_queue.files = None
