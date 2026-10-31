"""Linux child bootstrap: prevent descendants escaping an owned process group."""

import ctypes
import errno
import os
import platform
import socket
import sys


def install_group_guard():
    if sys.platform != "linux":
        raise OSError(errno.ENOTSUP, "Process containment prerequisite unavailable.")
    configurations = {
        "x86_64": (0xC000003E, (109, 112, 272, 308), 56, 435),
        "aarch64": (0xC00000B7, (157, 154, 97, 268), 220, 435),
    }
    if platform.machine() not in configurations:
        raise OSError(errno.ENOTSUP, "Process containment prerequisite unavailable.")
    architecture, forbidden, clone, clone3 = configurations[platform.machine()]

    class Filter(ctypes.Structure):
        _fields_ = [("code", ctypes.c_ushort), ("jt", ctypes.c_ubyte),
                    ("jf", ctypes.c_ubyte), ("k", ctypes.c_uint)]

    class Program(ctypes.Structure):
        _fields_ = [("length", ctypes.c_ushort), ("filters", ctypes.POINTER(Filter))]

    instructions = [
        (0x20, 0, 0, 4),                         # seccomp_data.arch
        (0x15, 1, 0, architecture),
        (0x06, 0, 0, 0x80000000),
        (0x20, 0, 0, 0),                         # seccomp_data.nr
        (0x35, 0, 1, 0x40000000),                # reject alternate x32 ABI
        (0x06, 0, 0, 0x00050000 | errno.EPERM),
    ]
    for number in forbidden:
        instructions.extend(((0x15, 0, 1, number), (0x06, 0, 0, 0x00050000 | errno.EPERM)))
    instructions.extend((
        (0x15, 0, 1, clone3),
        (0x06, 0, 0, 0x00050000 | errno.ENOSYS),  # libc falls back to inspectable clone
        (0x15, 0, 3, clone),
        (0x20, 0, 0, 16),                        # clone flags: seccomp_data.args[0]
        (0x45, 0, 1, 0x7E020000),                # namespace flags, including NEWCGROUP
        (0x06, 0, 0, 0x00050000 | errno.EPERM),
        (0x06, 0, 0, 0x7FFF0000),
    ))
    filters = (Filter * len(instructions))(*(Filter(*instruction) for instruction in instructions))
    program = Program(len(filters), filters)
    native = ctypes.CDLL(None, use_errno=True)
    native.prctl.restype = ctypes.c_int
    if native.prctl(38, 1, 0, 0, 0) or native.prctl(22, 2, ctypes.byref(program), 0, 0):
        raise OSError(ctypes.get_errno(), "Process containment prerequisite unavailable.")
    if native.prctl(21, 0, 0, 0, 0) != 2:
        raise OSError(errno.ENOTSUP, "Process containment prerequisite unavailable.")


def main():
    if len(sys.argv) < 3:
        return 2
    try:
        with socket.socket(fileno=int(sys.argv[1])) as acknowledgement:
            install_group_guard()
            acknowledgement.sendall(b"1")
            if acknowledgement.recv(1) != b"1":
                return 2
    except OSError:
        os.write(1, b'{"event":"control","code":"PrerequisiteMissing","value":0}\n')
        return 2
    try:
        os.execvpe(sys.argv[2], sys.argv[2:], os.environ)
    except OSError:
        os.write(1, b'{"event":"control","code":"CommandFailed","value":0}\n')
        return 2


if __name__ == "__main__":
    sys.exit(main())
