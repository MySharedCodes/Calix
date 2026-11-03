#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <filesystem>
#include <iostream>
#include <string>
#include <vector>

namespace {
std::wstring quote(const std::wstring& value) {
    std::wstring result = L"\"";
    size_t slashes = 0;
    for (wchar_t ch : value) {
        if (ch == L'\\') {
            ++slashes;
        } else {
            result.append(slashes * (ch == L'"' ? 2 : 1), L'\\');
            slashes = 0;
            if (ch == L'"') result += L'\\';
            result += ch;
        }
    }
    result.append(slashes * 2, L'\\');
    return result + L'"';
}

int failure(const char* message) {
    std::cout << "{\"ok\":false,\"error\":\"" << message << "\",\"error_type\":\"LauncherError\"}\n";
    return 2;
}

BOOL WINAPI handle_control(DWORD event) {
    // The calculation client handles Ctrl+C and cancels its active session.
    return event == CTRL_C_EVENT;
}
}

int wmain(int argc, wchar_t** argv) {
    std::vector<wchar_t> location(32768);
    const DWORD length = GetModuleFileNameW(nullptr, location.data(), static_cast<DWORD>(location.size()));
    if (!length || length >= location.size()) return failure("Cannot locate Calix runtime");
    const auto root = std::filesystem::path(std::wstring(location.data(), length)).parent_path();
    auto executable = root / L"backend/calix-service.exe";
    std::wstring command;
    if (std::filesystem::is_regular_file(executable)) {
        command = quote(executable.wstring()) + L" --cli";
    } else {
        executable = root / L".venv/Scripts/python.exe";
        if (!std::filesystem::is_regular_file(executable)) return failure("Calix calculation runtime is missing");
        const DWORD size = GetEnvironmentVariableW(L"PYTHONPATH", nullptr, 0);
        std::vector<wchar_t> old_path(size ? size : 1);
        if (size) GetEnvironmentVariableW(L"PYTHONPATH", old_path.data(), size);
        const std::wstring search = root.wstring() + L";" + old_path.data();
        if (!SetEnvironmentVariableW(L"PYTHONPATH", search.c_str())) return failure("Cannot configure Calix runtime");
        command = quote(executable.wstring()) + L" -m backend.cli";
    }
    for (int i = 1; i < argc; ++i) command += L" " + quote(argv[i]);
    STARTUPINFOW startup{};
    startup.cb = sizeof(startup);
    startup.dwFlags = STARTF_USESTDHANDLES;
    startup.hStdInput = GetStdHandle(STD_INPUT_HANDLE);
    startup.hStdOutput = GetStdHandle(STD_OUTPUT_HANDLE);
    startup.hStdError = GetStdHandle(STD_ERROR_HANDLE);
    PROCESS_INFORMATION process{};
    SetConsoleCtrlHandler(handle_control, TRUE);
    if (!CreateProcessW(executable.c_str(), command.data(), nullptr, nullptr, TRUE, 0,
                        nullptr, nullptr, &startup, &process)) return failure("Cannot start Calix calculation client");
    CloseHandle(process.hThread);
    WaitForSingleObject(process.hProcess, INFINITE);
    DWORD status = 2;
    GetExitCodeProcess(process.hProcess, &status);
    CloseHandle(process.hProcess);
    return static_cast<int>(status);
}
