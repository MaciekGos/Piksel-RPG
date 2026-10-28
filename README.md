# Piksel RPG

[![Windows](https://img.shields.io/badge/platform-Windows-blue)](https://github.com/MaciekGos/Piksel-RPG)
[![GNU GPL v3](https://img.shields.io/badge/license-GNU%20GPL%20v3-blue)](https://www.gnu.org/licenses/gpl-3.0.html)

A cooperative RPG with an AI Game Master powered by Llama. One player hosts the game and runs Llama locally, while the other players join using an invite code.

**No accounts, paid services, or central game server required.** The game runs directly on the players' computers.

- **AI Game Master:** Llama runs through Ollama, generates the story, edits a **256×256 pixel map**, and places markers such as towns, dungeons, hazards, and treasures.
- **P2P:** players connect directly to the host using an invite code.
- **Chronicle:** records who played each character and what happened during the campaign.
- **Local saves:** every player keeps their own copy of the game save.
- **Campaign start:** all living players must join and be ready before a new campaign can start.
- **Demo mode:** a scripted Game Master can be used without Ollama.

## Screenshots

### Menu & Setup

![Main Menu](screenshots/en/01-menu.png)

![New Campaign](screenshots/en/02-nowa-kampania.png)

![Random World](screenshots/en/02a-losowy-swiat.png)

### Multiplayer

![Host Lobby](screenshots/en/03-lobby-host.png)

![Join Game](screenshots/en/04-dolacz.png)

![Team Lobby](screenshots/en/05-lobby-druzyna.png)

![Player Lobby](screenshots/en/06-lobby-gracz.png)

![Ready Lobby](screenshots/en/07-lobby-gotowi.png)

### Gameplay

![Game Start](screenshots/en/08-gra-start.png)

![Waiting](screenshots/en/09-gra-czekamy.png)

![Round](screenshots/en/10-gra-runda.png)

![Defeated Players](screenshots/en/11-gra-poleglym.png)

![Characters](screenshots/en/12-postac-kto-jest-kim.png)

![Game End](screenshots/en/13-gra-koniec.png)

### Other

![Chronicle](screenshots/en/14-kronika.png)

![Settings](screenshots/en/15-ustawienia.png)

![Load Game](screenshots/en/16-wznow-zapis.png)

### Installer

![Installer Welcome](screenshots/en/17-instalator-powitanie.png)

![Installer Options](screenshots/en/18-instalator-opcje.png)

![Installation Progress](screenshots/en/19-instalator-postep.png)

![Installation Complete](screenshots/en/20-instalator-koniec.png)

### Other Screens

![Loading Minigame](screenshots/en/21-ladowanie-minigra.png)

![Leave Vote](screenshots/en/22-glosowanie-wyjscie.png)

![Death Exit](screenshots/en/23-wyjscie-zgon.png)

## Installation

```bash
pip install -r requirements.txt
python main.py
```

Installer:

```bash
python installer/install.py
```

Or use `PikselRPG-Setup.exe`.

Silent installation:

```text
--silent --dir DIRECTORY [--ollama] [--model llama3.2:3b]
```

## How to Play

1. **Host:** select *Host New Game*, enter a nickname, world name, description, and player count. The lobby provides invite codes for **Global**, **LAN/VPN**, and **Internet** connections.
2. **Players:** select *Join Game* and enter a nickname and invite code. Each player creates a character and marks themselves as ready.
3. The host starts the game once everyone is ready. Llama generates the world, map, markers, and opening narration.
4. Each round, living players submit one action. The game engine handles dice rolls and outcomes, while the Game Master describes what happens and updates the world.
5. Dead players can continue watching the game and use the chat.
6. Saved campaigns can be resumed by any participant who has a copy of the save.

## Networking

The game does not require paid networking services.

- **LAN/VPN:** connect through the same network or a VPN such as Tailscale, ZeroTier, or Radmin.
- **Global:** the default connection method uses a public TCP tunnel based on `bore`. The client is built into the game.
- **Internet:** the host can attempt to open TCP port `47600` automatically using UPnP. Manual port forwarding can also be used.
- Public IP detection uses `api.ipify.org` and is optional.

Traffic through the public tunnel is not encrypted. Access is protected by a random token included in the invite code. Do not share invite codes for private games.

## Llama

The host can install [Ollama](https://ollama.com) and download a model from the game settings.

Default model:

```text
llama3.2:3b
```

A larger model such as:

```text
llama3.1:8b
```

can be used if more RAM is available.

Models without native tool support are also supported. JSON tool calls embedded in model output are parsed by the game.

## Windows Installer

Build the Windows installer with:

```bash
py -m pip install pyinstaller PySide6-Essentials
py tools\build_windows.py
```

Output:

```text
dist\PikselRPG-Setup.exe
```

The installer does not require administrator privileges for the basic installation. It can optionally install Ollama, download the selected model, and add the required firewall rule through UAC.

## Tests

Run the core test suite:

```bash
python tests/test_core.py
```

Generate screenshots:

```bash
QT_QPA_PLATFORM=offscreen python tools/make_screenshots.py screenshots
```

## Recent Changes

- AI-generated character roles instead of fixed classes.
- Random world generation.
- Updated Game Master prompt and narration handling.
- Persistent maps that are generated once and then edited during gameplay.
- Multiplayer loading minigame.
- System TTS support on Windows, macOS, and Linux.
- Vote-based game exit system.
- English language support in the game and installer.
- P2P Internet connectivity using the `bore` tunnel.
- Local saves for every participant.

## Resource Licenses

- Phosphor Icons — MIT
- Pixelify Sans / Inter — SIL Open Font License
- Logo — custom
- Qt / PySide6 — LGPL
- Ollama — MIT
- Llama models — subject to Meta's applicable license

## Building

The Windows build scripts can be run in order:

```text
1_przygotuj.bat
2_zasoby.bat
3_testy.bat
4_buduj_instalator.bat
5_uruchom_instalator.bat
```

The installer is generated at:

```text
dist\PikselRPG-Setup.exe
```

For quick testing:

```text
uruchom_gre.bat
uruchom_instalator_ze_zrodel.bat
```

Python 3.10+ is required.
