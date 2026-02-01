from plyer import notification

def notify_new_dxcc(country, call, mode, snr):
    notification.notify(
        title="New DXCC spotted!",
        message=f"{country}\n{call} | {mode} | {snr} dB",
        timeout=6
    )
