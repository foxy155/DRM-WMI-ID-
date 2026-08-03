import wmi
import hashlib

def get_hardware_fingerprint():
    """Collects stable hardware IDs and generates a unique system fingerprint."""
    c = wmi.WMI()
    ids = {}

    # 1. CPU ID (Very stable)
    for cpu in c.Win32_Processor():
        ids['cpu'] = cpu.ProcessorId.strip()
        break

    # 2. Motherboard UUID (Very stable, built into BIOS)
    for csproduct in c.Win32_ComputerSystemProduct():
        ids['uuid'] = csproduct.UUID.strip()
        break

    # 3. Motherboard Serial Number
    for board in c.Win32_BaseBoard():
        ids['motherboard'] = board.SerialNumber.strip()
        break

    # 4. Hard Drive Serial Number (First physical non-USB drive)
    for disk in c.Win32_DiskDrive():
        if 'USB' not in disk.Caption and 'SD' not in disk.Caption:
            ids['disk'] = disk.SerialNumber.strip()
            break

    # Combine the IDs into a single string
    raw_string = f"{ids.get('cpu', '')}-{ids.get('uuid', '')}-{ids.get('motherboard', '')}-{ids.get('disk', '')}"

    # Generate the final fingerprint using SHA-256
    fingerprint = hashlib.sha256(raw_string.encode()).hexdigest()

    return ids, fingerprint

if __name__ == "__main__":
    print("Collecting Hardware DNA...")
    ids, fp = get_hardware_fingerprint()

    print("\nCollected IDs:")
    for key, value in ids.items():
        print(f"  {key}: {value}")

    print(f"\nSystem Fingerprint: {fp}")
    print("\nRun this on 3 different computers. Each will have a unique hash!")
