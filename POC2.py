import hashlib
import time
import numpy as np
import sys

# ============================================================
# CONFIGURATION
# ============================================================
SERVER_SALT = "UltraSecretSalt_2025"
TIMING_TOLERANCE = 0.15  # 15% tolerance for timing variations

# ============================================================
# PHASE 1: HARDWARE FINGERPRINT (WMI Simulation)
# ============================================================
try:
    import wmi
    HAS_WMI = True
except ImportError:
    HAS_WMI = False
    print("[!] WMI module not found. Using mock hardware IDs for demonstration.")
    print("[!] Install 'pip install wmi pywin32' for real hardware readings.\n")

def get_hardware_ids():
    """Reads actual hardware IDs using WMI, or returns mock data if unavailable."""
    # Initialize with safe defaults
    ids = {
        'cpu': 'UNKNOWN_CPU',
        'uuid': 'UNKNOWN_UUID',
        'motherboard': 'UNKNOWN_MOTHERBOARD',
        'disk': 'UNKNOWN_DISK',
        'ram': 'SKIP_RAM'
    }

    if HAS_WMI:
        try:
            c = wmi.WMI()

            for cpu in c.Win32_Processor():
                if cpu.ProcessorId:
                    ids['cpu'] = cpu.ProcessorId.strip()
                break

            for csproduct in c.Win32_ComputerSystemProduct():
                if csproduct.UUID:
                    ids['uuid'] = csproduct.UUID.strip()
                break

            for board in c.Win32_BaseBoard():
                if board.SerialNumber:
                    ids['motherboard'] = board.SerialNumber.strip()
                break

            for disk in c.Win32_DiskDrive():
                caption = disk.Caption.lower() if disk.Caption else ""
                if 'usb' not in caption and 'sd' not in caption and disk.SerialNumber:
                    ids['disk'] = disk.SerialNumber.strip()
                    break

            return ids
        except Exception as e:
            print(f"[!] WMI read error: {e}. Using mock data.")
            return get_mock_ids()
    else:
        return get_mock_ids()

def get_mock_ids():
    """Returns deterministic mock IDs for testing without WMI."""
    return {
        'cpu': 'BFEBFBFF000B0671_MOCK',
        'uuid': '9E957B75-EBEC-D919-A99E-047C16EE819B_MOCK',
        'motherboard': '07D4830_N81E357758_MOCK',
        'disk': 'S3Z5NS0M123456_MOCK',
        'ram': 'SKIP_RAM'
    }

def generate_device_fingerprint(ids, salt):
    """Combines hardware IDs with salt and generates a SHA-256 fingerprint."""
    raw_string = f"{ids['cpu']}-{ids['uuid']}-{ids['motherboard']}-{ids['disk']}-{salt}"
    return hashlib.sha256(raw_string.encode()).hexdigest()

# ============================================================
# PHASE 3: PHYSICAL ATTESTATION (CPU Timing Signature)
# ============================================================
def measure_cpu_speed_limit(iterations=8000):
    """Measures the absolute fastest execution speed of the CPU."""
    timings = []

    # Warm-up
    x = 1.23456789
    for _ in range(1000):
        x = (x * 3.14159) % 2.71828

    # Actual measurement
    for _ in range(iterations):
        start = time.perf_counter_ns()
        x = 1.23456789
        for i in range(50):
            x = (x * 3.14159) % 2.71828
        end = time.perf_counter_ns()
        timings.append(end - start)

    sorted_timings = np.sort(timings)
    fastest_count = max(1, int(len(sorted_timings) * 0.01))
    fastest_samples = sorted_timings[:fastest_count]
    base_speed = np.mean(fastest_samples)

    return base_speed

# ============================================================
# SERVER SIMULATION (In-memory database)
# ============================================================
class ServerDB:
    def __init__(self):
        self.devices = {}  # DFP -> {specs, timing, accounts}
        self.accounts = {}  # AccountID -> {dfp, banned}

    def register_device(self, dfp, specs, timing):
        """Phase 1: First-time registration."""
        if dfp in self.devices:
            return "DEVICE_EXISTS"

        self.devices[dfp] = {
            'specs': specs,
            'timing': timing,
            'accounts': 0
        }
        return "REGISTERED"

    def verify_login(self, dfp, account_id, specs, timing):
        """Phases 2 & 3: Full attestation."""
        # Check if device exists
        if dfp not in self.devices:
            return "UNREGISTERED_DEVICE"

        device = self.devices[dfp]
        baseline_specs = device['specs']
        baseline_timing = device['timing']

        # --- PHASE 2: Account History & Spoofing Detection ---
        # Check if account exists
        if account_id in self.accounts:
            if self.accounts[account_id]['banned']:
                return "ACCOUNT_BANNED"
            if self.accounts[account_id]['dfp'] != dfp:
                return "BAN_ACCOUNT_MISMATCH"

        # Check hardware specs against baseline
        if specs != baseline_specs:
            return "BAN_HARDWARE_SPOOF"

        # --- PHASE 3: Physical Attestation (CPU Timing) ---
        diff_percent = abs(timing - baseline_timing) / baseline_timing
        if diff_percent > TIMING_TOLERANCE:
            return f"BAN_TIMING_MISMATCH (Diff: {diff_percent*100:.1f}%)"

        # --- SUCCESS ---
        if account_id not in self.accounts:
            if device['accounts'] >= 2:
                return "MAX_ACCOUNTS_EXCEEDED"
            self.accounts[account_id] = {'dfp': dfp, 'banned': False}
            device['accounts'] += 1

        return "AUTHENTICATED"

# ============================================================
# SIMULATION SCENARIOS
# ============================================================
def run_scenario(server, scenario_name, client_ids, account_id, simulate_spoof=False, simulate_vm=False):
    print(f"\n{'='*60}")
    print(f"SCENARIO: {scenario_name}")
    print(f"{'='*60}")

    # Step 1: Generate Device Fingerprint (Phase 1)
    dfp = generate_device_fingerprint(client_ids, SERVER_SALT)
    print(f"[1] Device Fingerprint (DFP): {dfp[:16]}...{dfp[-16:]}")

    # Step 2: Measure CPU Timing (Phase 3)
    if simulate_vm:
        timing = measure_cpu_speed_limit() * 2.1
        print(f"[2] CPU Timing Signature: {timing:.2f} ns (SIMULATED VM SLOWDOWN)")
    else:
        timing = measure_cpu_speed_limit()
        print(f"[2] CPU Timing Signature: {timing:.2f} ns")

    # Step 3: Print Hardware Specs
    print(f"[3] Hardware Specs:")
    for k, v in client_ids.items():
        print(f"      {k}: {v}")

    # Step 4: Register the device FIRST (Phase 1) - Only for legitimate devices
    if not simulate_spoof:
        registration_result = server.register_device(dfp, client_ids, timing)
        print(f"[4] Device Registration: {registration_result}")

    # Step 5: Server verification (Phases 2 & 3)
    if simulate_spoof:
        spoofed_specs = client_ids.copy()
        spoofed_specs['motherboard'] = "FAKE_MOTHERBOARD_12345"
        print(f"[5] Server Verification (SIMULATED SPOOFING):")
        result = server.verify_login(dfp, account_id, spoofed_specs, timing)
    else:
        print(f"[5] Server Verification:")
        result = server.verify_login(dfp, account_id, client_ids, timing)

    # Step 6: Print result
    print(f"\n>>> RESULT: {result}")
    if result == "AUTHENTICATED":
        print("   ✅ ACCESS GRANTED. Game launches.")
    elif result == "REGISTERED":
        print("   📝 New device registered in database.")
    elif result.startswith("BAN"):
        print(f"   🚫 ACCESS DENIED. {result}")
    else:
        print(f"   ⚠️ {result}")

    return result

# ============================================================
# MAIN EXECUTION
# ============================================================
if __name__ == "__main__":
    print("\n" + "="*60)
    print("🔥 HARDWARE ATTESTATION POC (3-Phase System)")
    print("="*60)
    print("\nThis POC demonstrates how the system catches:")
    print("  - Phase 1: Hardware Binding (WMI + Salt + Hash)")
    print("  - Phase 2: Account History & Spoofing Detection")
    print("  - Phase 3: Physical Attestation (CPU Timing Jitter)")
    print("\n" + "="*60)

    server = ServerDB()

    print("\n[+] Reading hardware IDs from this machine...")
    real_ids = get_hardware_ids()

    # --- SCENARIO 1: First-time Registration ---
    run_scenario(server, "1. NEW DEVICE REGISTRATION", real_ids, "Account_A")

    # --- SCENARIO 2: Legitimate Login ---
    run_scenario(server, "2. LEGITIMATE LOGIN", real_ids, "Account_A")

    # --- SCENARIO 3: Spoofing Attempt ---
    run_scenario(server, "3. SPOOFING ATTEMPT (Fake Motherboard)", real_ids, "Account_B", simulate_spoof=True)

    # --- SCENARIO 4: VM / Emulation Attack ---
    run_scenario(server, "4. VM/EMULATION ATTACK (Slow Timing)", real_ids, "Account_C", simulate_vm=True)

    # --- SCENARIO 5: Second Legitimate Account ---
    run_scenario(server, "5. SECOND LEGITIMATE ACCOUNT (Same Device)", real_ids, "Account_D")

    # --- SCENARIO 6: Third Account (Should fail) ---
    run_scenario(server, "6. THIRD ACCOUNT (Should exceed limit)", real_ids, "Account_E")

    print("\n" + "="*60)
    print("🏁 POC COMPLETE")
    print("="*60)
    print("\nSummary:")
    print("  Scenario 1: New device registered.")
    print("  Scenario 2: Legit login → ✅ PASSED (Phase 2 & 3 verified).")
    print("  Scenario 3: Spoofed motherboard → 🚫 BANNED (Phase 2 caught it).")
    print("  Scenario 4: VM/Emulation timing mismatch → 🚫 BANNED (Phase 3 caught it).")
    print("  Scenario 5: Second account on same device → ✅ PASSED (Limit allows 2).")
    print("  Scenario 6: Third account on same device → 🚫 DENIED (Exceeded limit).")
