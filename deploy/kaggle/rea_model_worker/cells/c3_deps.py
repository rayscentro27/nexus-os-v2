# ===================== CELL 3 — DEPENDENCY SETUP =====================
# Minimum inference stack: llama.cpp llama-server (CUDA, GGUF) + fastapi/uvicorn/httpx proxy.
# huggingface_hub is preinstalled in the Kaggle image. No transformers/vLLM/bitsandbytes needed for GGUF.
LLAMA_SERVER = WORK / "llama.cpp" / "build" / "bin" / "llama-server"
if BLOCKER is None:
    t0 = time.time()
    missing = []
    for spec in PIP_PACKAGES:
        mod = spec.split("==")[0]
        try:
            __import__(mod)
        except ImportError:
            missing.append(spec)
    if missing:
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", *missing], check=True)
    import fastapi, uvicorn, httpx, huggingface_hub
    pkgs = {"fastapi": fastapi.__version__, "uvicorn": uvicorn.__version__, "httpx": httpx.__version__,
            "huggingface_hub": huggingface_hub.__version__}
    if not LLAMA_SERVER.exists():
        src = WORK / "llama.cpp"
        subprocess.run(["git", "clone", "--quiet", "--depth", "1", "--branch", LLAMA_CPP_TAG,
                        "https://github.com/ggml-org/llama.cpp.git", str(src)], check=True)
        head = subprocess.run(["git", "-C", str(src), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        if head != LLAMA_CPP_COMMIT:
            raise RuntimeError(f"LLAMA_CPP_COMMIT_MISMATCH {head}")
        # Flags proven on Kaggle T4 (sm_75); NO_VMM avoids the CUDA VMM failure seen with prebuilt binaries.
        subprocess.run(["cmake", "-S", str(src), "-B", str(src / "build"), "-DCMAKE_BUILD_TYPE=Release", "-DGGML_CUDA=ON",
                        "-DGGML_CUDA_NO_VMM=ON", "-DGGML_NATIVE=OFF", "-DCMAKE_CUDA_ARCHITECTURES=75-real",
                        "-DLLAMA_BUILD_TESTS=OFF", "-DLLAMA_BUILD_EXAMPLES=OFF", "-DLLAMA_BUILD_SERVER=ON", "-DLLAMA_CURL=OFF"],
                       check=True, stdout=subprocess.DEVNULL)
        build = subprocess.run(["cmake", "--build", str(src / "build"), "--target", "llama-server", "-j", str(os.cpu_count() or 4)],
                               capture_output=True, text=True)
        (OUT / "llama_build_tail.log").write_text(build.stdout[-8000:] + build.stderr[-8000:])
        if build.returncode != 0:
            raise RuntimeError("LLAMA_SERVER_BUILD_FAILED")
    pkgs["llama.cpp"] = f"{LLAMA_CPP_TAG} ({LLAMA_CPP_COMMIT[:12]})"
    kv("PACKAGES_INSTALLED", json.dumps(pkgs))
    kv("PACKAGE_INSTALL_STATUS", "PASS")
    kv("DEPENDENCY_SETUP_SECONDS", round(time.time() - t0, 1))
