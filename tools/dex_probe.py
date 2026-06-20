#!/usr/bin/env python3
import argparse
import bisect
import io
import struct
from dataclasses import dataclass


def uleb128(data: bytes, off: int):
    result = 0
    shift = 0
    start = off
    while True:
        b = data[off]
        off += 1
        result |= (b & 0x7F) << shift
        if (b & 0x80) == 0:
            return result, off
        shift += 7
        if off - start > 5:
            raise ValueError("uleb128 too long")


class Dex:
    def __init__(self, path: str):
        self.path = path
        self.data = open(path, "rb").read()
        d = self.data
        if d[:8] != b"dex\n035\x00":
            raise ValueError(f"{path}: unsupported dex header {d[:8]!r}")
        self.string_ids_size, self.string_ids_off = struct.unpack_from("<II", d, 0x38)
        self.type_ids_size, self.type_ids_off = struct.unpack_from("<II", d, 0x40)
        self.proto_ids_size, self.proto_ids_off = struct.unpack_from("<II", d, 0x48)
        self.field_ids_size, self.field_ids_off = struct.unpack_from("<II", d, 0x50)
        self.method_ids_size, self.method_ids_off = struct.unpack_from("<II", d, 0x58)
        self.class_defs_size, self.class_defs_off = struct.unpack_from("<II", d, 0x60)
        self._strings = None
        self._types = None
        self._protos = None
        self._fields = None
        self._methods = None
        self._class_defs = None
        self._code_items = None

    @property
    def strings(self):
        if self._strings is None:
            arr = []
            for i in range(self.string_ids_size):
                (off,) = struct.unpack_from("<I", self.data, self.string_ids_off + i * 4)
                utf16_len, p = uleb128(self.data, off)
                end = self.data.index(b"\x00", p)
                try:
                    s = self.data[p:end].decode("utf-8")
                except UnicodeDecodeError:
                    s = self.data[p:end].decode("utf-8", errors="replace")
                arr.append((off, utf16_len, s))
            self._strings = arr
        return self._strings

    @property
    def types(self):
        if self._types is None:
            arr = []
            for i in range(self.type_ids_size):
                (string_idx,) = struct.unpack_from("<I", self.data, self.type_ids_off + i * 4)
                arr.append(self.strings[string_idx][2])
            self._types = arr
        return self._types

    @property
    def protos(self):
        if self._protos is None:
            arr = []
            for i in range(self.proto_ids_size):
                shorty_idx, return_type_idx, parameters_off = struct.unpack_from(
                    "<III", self.data, self.proto_ids_off + i * 12
                )
                params = []
                if parameters_off != 0:
                    (size,) = struct.unpack_from("<I", self.data, parameters_off)
                    for j in range(size):
                        (type_idx,) = struct.unpack_from("<H", self.data, parameters_off + 4 + j * 2)
                        params.append(self.types[type_idx])
                arr.append(
                    {
                        "shorty": self.strings[shorty_idx][2],
                        "return_type": self.types[return_type_idx],
                        "parameters": params,
                        "descriptor": f"({' '.join(params)}){self.types[return_type_idx]}",
                    }
                )
            self._protos = arr
        return self._protos

    @property
    def fields(self):
        if self._fields is None:
            arr = []
            for i in range(self.field_ids_size):
                class_idx, type_idx, name_idx = struct.unpack_from("<HHI", self.data, self.field_ids_off + i * 8)
                arr.append(
                    {
                        "class_idx": class_idx,
                        "type_idx": type_idx,
                        "name_idx": name_idx,
                        "class_desc": self.types[class_idx],
                        "type_desc": self.types[type_idx],
                        "name": self.strings[name_idx][2],
                    }
                )
            self._fields = arr
        return self._fields

    @property
    def methods(self):
        if self._methods is None:
            arr = []
            for i in range(self.method_ids_size):
                class_idx, proto_idx, name_idx = struct.unpack_from("<HHI", self.data, self.method_ids_off + i * 8)
                arr.append(
                    {
                        "class_idx": class_idx,
                        "proto_idx": proto_idx,
                        "name_idx": name_idx,
                        "class_desc": self.types[class_idx],
                        "proto": self.protos[proto_idx],
                        "descriptor": self.protos[proto_idx]["descriptor"],
                        "name": self.strings[name_idx][2],
                    }
                )
            self._methods = arr
        return self._methods

    @property
    def class_defs(self):
        if self._class_defs is None:
            arr = []
            for i in range(self.class_defs_size):
                vals = struct.unpack_from("<IIIIIIII", self.data, self.class_defs_off + i * 32)
                class_idx, access_flags, super_idx, interfaces_off, source_file_idx, annotations_off, class_data_off, static_values_off = vals
                arr.append(
                    {
                        "class_idx": class_idx,
                        "class_desc": self.types[class_idx],
                        "access_flags": access_flags,
                        "super_idx": super_idx,
                        "super_desc": self.types[super_idx] if super_idx != 0xFFFFFFFF else None,
                        "interfaces_off": interfaces_off,
                        "source_file_idx": source_file_idx,
                        "source_file": self.strings[source_file_idx][2] if source_file_idx != 0xFFFFFFFF else None,
                        "annotations_off": annotations_off,
                        "class_data_off": class_data_off,
                        "static_values_off": static_values_off,
                    }
                )
            self._class_defs = arr
        return self._class_defs

    def class_data(self, class_desc: str):
        target = None
        for c in self.class_defs:
            if c["class_desc"] == class_desc:
                target = c
                break
        if not target:
            return None
        off = target["class_data_off"]
        if off == 0:
            return {"class_def": target, "static_fields": [], "instance_fields": [], "direct_methods": [], "virtual_methods": []}
        data = self.data
        sf_size, off = uleb128(data, off)
        if_size, off = uleb128(data, off)
        dm_size, off = uleb128(data, off)
        vm_size, off = uleb128(data, off)

        def read_fields(n, off):
            out = []
            field_idx = 0
            for _ in range(n):
                diff, off = uleb128(data, off)
                access_flags, off = uleb128(data, off)
                field_idx += diff
                fd = dict(self.fields[field_idx])
                fd["field_idx"] = field_idx
                fd["access_flags"] = access_flags
                out.append(fd)
            return out, off

        def read_methods(n, off):
            out = []
            method_idx = 0
            for _ in range(n):
                diff, off = uleb128(data, off)
                access_flags, off = uleb128(data, off)
                code_off, off = uleb128(data, off)
                method_idx += diff
                md = dict(self.methods[method_idx])
                md["method_idx"] = method_idx
                md["access_flags"] = access_flags
                md["code_off"] = code_off
                out.append(md)
            return out, off

        static_fields, off = read_fields(sf_size, off)
        instance_fields, off = read_fields(if_size, off)
        direct_methods, off = read_methods(dm_size, off)
        virtual_methods, off = read_methods(vm_size, off)
        return {
            "class_def": target,
            "static_fields": static_fields,
            "instance_fields": instance_fields,
            "direct_methods": direct_methods,
            "virtual_methods": virtual_methods,
        }

    def method_by_idx(self, idx: int):
        if idx < 0 or idx >= len(self.methods):
            return None
        md = dict(self.methods[idx])
        md["method_idx"] = idx
        return md

    def all_class_methods(self):
        for cls in self.class_defs:
            cd = self.class_data(cls["class_desc"])
            for kind in ("direct_methods", "virtual_methods"):
                for m in cd[kind]:
                    item = dict(m)
                    item["kind"] = kind
                    yield item

    def find_methods_by_idx(self, idx: int):
        for m in self.all_class_methods():
            if m["method_idx"] == idx:
                yield m

    def find_methods_by_code_off(self, code_off: int):
        for m in self.all_class_methods():
            if m["code_off"] == code_off:
                yield m

    def string_hits(self, needle: str):
        hits = []
        for idx, (off, _utf16_len, s) in enumerate(self.strings):
            if s == needle:
                hits.append((idx, off, s))
        return hits


def cmd_strings(dx: Dex, needle: str):
    for idx, off, s in dx.string_hits(needle):
        print(f"string_idx={idx} off=0x{off:x} value={s!r}")


def cmd_class(dx: Dex, desc: str):
    cd = dx.class_data(desc)
    if not cd:
        print(f"class not found: {desc}")
        return
    cls = cd["class_def"]
    print(f"class={cls['class_desc']} super={cls['super_desc']} source={cls['source_file']!r} class_data_off=0x{cls['class_data_off']:x}")
    print("static_fields:")
    for f in cd["static_fields"]:
        print(f"  idx={f['field_idx']} {f['name']} {f['type_desc']} flags=0x{f['access_flags']:x}")
    print("instance_fields:")
    for f in cd["instance_fields"]:
        print(f"  idx={f['field_idx']} {f['name']} {f['type_desc']} flags=0x{f['access_flags']:x}")
    print("direct_methods:")
    for m in cd["direct_methods"]:
        print(f"  idx={m['method_idx']} {m['name']} code_off=0x{m['code_off']:x} flags=0x{m['access_flags']:x}")
    print("virtual_methods:")
    for m in cd["virtual_methods"]:
        print(f"  idx={m['method_idx']} {m['name']} code_off=0x{m['code_off']:x} flags=0x{m['access_flags']:x}")


def cmd_fields(dx: Dex, name: str):
    for i, f in enumerate(dx.fields):
        if f["name"] == name:
            print(f"field_idx={i} class={f['class_desc']} name={f['name']} type={f['type_desc']}")


def cmd_methods(dx: Dex, name: str):
    for i, m in enumerate(dx.methods):
        if m["name"] == name:
            print(f"method_idx={i} class={m['class_desc']} name={m['name']} desc={m['descriptor']}")


def cmd_method_idx(dx: Dex, idx: int):
    m = dx.method_by_idx(idx)
    if not m:
        print(f"method_idx out of range: {idx}")
        return
    print(
        f"method_idx={idx} class={m['class_desc']} name={m['name']} "
        f"proto_idx={m['proto_idx']} desc={m['descriptor']}"
    )
    found = False
    for item in dx.find_methods_by_idx(idx):
        found = True
        print(
            f"  defined_in={item['class_desc']} kind={item['kind']} "
            f"code_off=0x{item['code_off']:x} flags=0x{item['access_flags']:x}"
        )
    if not found:
        print("  not defined in any class_data (external/reference only)")


def cmd_code_off(dx: Dex, code_off: int):
    found = False
    for m in dx.find_methods_by_code_off(code_off):
        found = True
        print(
            f"code_off=0x{code_off:x} method_idx={m['method_idx']} class={m['class_desc']} "
            f"name={m['name']} desc={m['descriptor']} kind={m['kind']} flags=0x{m['access_flags']:x}"
        )
    if not found:
        print(f"no method found with code_off=0x{code_off:x}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dex")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("strings")
    p.add_argument("needle")
    p = sub.add_parser("class")
    p.add_argument("desc")
    p = sub.add_parser("fields")
    p.add_argument("name")
    p = sub.add_parser("methods")
    p.add_argument("name")
    p = sub.add_parser("method_idx")
    p.add_argument("idx", type=int)
    p = sub.add_parser("code_off")
    p.add_argument("code_off", type=lambda x: int(x, 0))
    ns = ap.parse_args()

    dx = Dex(ns.dex)
    if ns.cmd == "strings":
        cmd_strings(dx, ns.needle)
    elif ns.cmd == "class":
        cmd_class(dx, ns.desc)
    elif ns.cmd == "fields":
        cmd_fields(dx, ns.name)
    elif ns.cmd == "methods":
        cmd_methods(dx, ns.name)
    elif ns.cmd == "method_idx":
        cmd_method_idx(dx, ns.idx)
    elif ns.cmd == "code_off":
        cmd_code_off(dx, ns.code_off)


if __name__ == "__main__":
    main()
