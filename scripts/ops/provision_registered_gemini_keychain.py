#!/usr/bin/env python3
"""Securely provision the already-registered Gemini key in macOS Keychain.

The secret is read from a no-echo terminal prompt and passed directly to
Security.framework. It is never written to a file, shell command line, or log.
"""
from __future__ import annotations

import ctypes
import getpass
import sys


SERVICE = "nexus/credential.google.gemini.prod.v1"
ACCOUNT = "api_key"
ERR_SEC_ITEM_NOT_FOUND = -25300


def _security_framework():
    if sys.platform != "darwin":
        raise RuntimeError("MACOS_KEYCHAIN_REQUIRED")
    framework = ctypes.CDLL(
        "/System/Library/Frameworks/Security.framework/Versions/Current/Security"
    )
    framework.SecKeychainFindGenericPassword.argtypes = [
        ctypes.c_void_p, ctypes.c_uint32, ctypes.c_char_p,
        ctypes.c_uint32, ctypes.c_char_p, ctypes.POINTER(ctypes.c_uint32),
        ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_void_p),
    ]
    framework.SecKeychainFindGenericPassword.restype = ctypes.c_int32
    framework.SecKeychainAddGenericPassword.argtypes = [
        ctypes.c_void_p, ctypes.c_uint32, ctypes.c_char_p,
        ctypes.c_uint32, ctypes.c_char_p, ctypes.c_uint32,
        ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p),
    ]
    framework.SecKeychainAddGenericPassword.restype = ctypes.c_int32
    framework.SecKeychainItemFreeContent.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    framework.SecKeychainItemFreeContent.restype = ctypes.c_int32
    return framework


def _find(framework):
    service = SERVICE.encode("ascii")
    account = ACCOUNT.encode("ascii")
    length = ctypes.c_uint32()
    data = ctypes.c_void_p()
    status = framework.SecKeychainFindGenericPassword(
        None, len(service), service, len(account), account,
        ctypes.byref(length), ctypes.byref(data), None,
    )
    if status == 0:
        try:
            return length.value > 0
        finally:
            framework.SecKeychainItemFreeContent(None, data)
    if status == ERR_SEC_ITEM_NOT_FOUND:
        return False
    raise RuntimeError(f"KEYCHAIN_LOOKUP_FAILED:{status}")


def main() -> int:
    try:
        security = _security_framework()
        if _find(security):
            print("KEYCHAIN_ENTRY_ALREADY_PRESENT; no change made")
            return 0

        first = getpass.getpass("Gemini API key (input hidden): ")
        second = getpass.getpass("Confirm Gemini API key (input hidden): ")
        if not first or first != second or first.strip() != first:
            print("INPUT_REJECTED; key was not stored")
            return 2

        secret = bytearray(first.encode("utf-8"))
        buffer = ctypes.create_string_buffer(len(secret))
        ctypes.memmove(buffer, (ctypes.c_ubyte * len(secret)).from_buffer(secret), len(secret))
        service = SERVICE.encode("ascii")
        account = ACCOUNT.encode("ascii")
        try:
            status = security.SecKeychainAddGenericPassword(
                None, len(service), service, len(account), account,
                len(secret), ctypes.cast(buffer, ctypes.c_void_p), None,
            )
        finally:
            ctypes.memset(buffer, 0, len(secret))
            for index in range(len(secret)):
                secret[index] = 0
            del first, second

        if status != 0:
            raise RuntimeError(f"KEYCHAIN_STORE_FAILED:{status}")
        if not _find(security):
            raise RuntimeError("KEYCHAIN_POST_STORE_VERIFY_FAILED")
        print("KEYCHAIN_ENTRY_STORED_AND_VERIFIED; secret not displayed")
        return 0
    except (OSError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
