# bulldozer
Donkeycar5.1.xを使った自律走行するタミヤ工作シリーズブルドーザ


## Raspberry Pi5セットアップ

- `sudo apt-get update --allow-releaseinfo-change && sudo apt-get upgrade -y`
- `sudo raspi-config`
    - Interfacing Options - I2C
    - Advanced Options - Expand Filesystem
    - Finish - 再起動される
- Kimi K2 をClaude Codeで使用する場合:
    - `echo "export ANTHROPIC_BASE_URL=https://api.moonshot.ai/anthropic" >> ~/.bashrc
    - `echo "ANTHROPIC_AUTH_TOKEN=sk-XXXXXXXXXXXXXXXXXXXXXXXXXXX" >> ~/.bashrc
- `cd && python3 -m venv env --system-site-packages`
- `echo "source ~/env/bin/activate" >> ~/.bashrc`
- `source ~/.bashrc`
- `sudo apt install -y libcap-dev libhdf5-dev libhdf5-serial-dev git`
- `pip install donkeycar[pi]`
- Claude Codeを使用する場合:
    - `sudo apt install -y ca-certificates curl gnupg`
    - `curl -sL https://deb.nodesource.com/setup_24.x | sudo -E bash -`
    - `npm install -g @anthropic-ai/claude-code`

- `cd ~/projects && git clone https://github.com/coolerking/bulldozer.git

