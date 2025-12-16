#!/usr/bin/env bash
set -euo pipefail

# detect_pi.sh - summary of OS, kernel, board and firmware info for Raspberry Pi

print_os() {
  if [ -f /etc/os-release ]; then
    . /etc/os-release
    echo "OS: ${PRETTY_NAME:-$NAME $VERSION}" 
    return
  fi
  if command -v lsb_release >/dev/null 2>&1; then
    echo "OS: $(lsb_release -ds)"
    return
  fi
  local fallback
  fallback=$(cat /etc/*release 2>/dev/null | head -n1 || true)
  if [ -n "$fallback" ]; then
    echo "OS: $fallback"
  else
    echo "OS: Unknown"
  fi
}

print_kernel() {
  echo "Kernel: $(uname -sr)"
}

print_board() {
  if [ -f /proc/device-tree/model ]; then
    # device-tree strings are NUL-terminated
    echo -n "Board: "
    tr -d '\0' </proc/device-tree/model
  else
    # try /proc/cpuinfo
    local model
    model=$(grep -m1 'Model' /proc/cpuinfo 2>/dev/null || true)
    if [ -n "$model" ]; then
      echo "${model#*: }"
    else
      echo "Board: Unknown"
    fi
  fi
}

print_cpuinfo() {
  if [ -f /proc/cpuinfo ]; then
    local cpu
    cpu=$(grep -m1 'Hardware' /proc/cpuinfo 2>/dev/null || grep -m1 'model name' /proc/cpuinfo 2>/dev/null || true)
    if [ -n "$cpu" ]; then
      echo "CPU: ${cpu#*: }"
    fi
  fi
}

print_vcgencmd() {
  if command -v vcgencmd >/dev/null 2>&1; then
    echo "Firmware: $(vcgencmd version | head -n1)"
    echo "Temp: $(vcgencmd measure_temp)"
  fi
}

main() {
  print_os
  print_kernel
  print_board
  print_cpuinfo
  print_vcgencmd
}

main
