# Piksel RPG

[![Windows](https://img.shields.io/badge/platform-Windows-blue)](https://github.com/MaciekGos/Piksel-RPG)
[![GNU GPL v3](https://img.shields.io/badge/license-GNU%20GPL%20v3-blue)](https://www.gnu.org/licenses/gpl-3.0.html)

A cooperative RPG with an AI Game Master powered by Llama. One player hosts the game and runs Llama locally, while the other players join using an invite code.

**No accounts, paid services, or central game server required.** The game runs directly on the players' computers. Multiplayer connections can use LAN/VPN, a public `bore` tunnel, or direct Internet connections.

* **AI Game Master:** Llama runs through Ollama, generates the story, edits a **256×256 pixel map**, and places markers such as towns, dungeons, hazards, and treasures.
* **Multiplayer:** players join the host using an invite code.
* **Chronicle:** records who played each character and what happened during the campaign.
* **Local saves:** every player keeps their own copy of the game save.
* **Campaign start:** all living players must join and be ready before a new campaign can start.
* **Demo mode:** a scripted Game Master can be used without Ollama.

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

### Windows installer

If you use the pre-built `PikselRPG-Setup.exe`, **Python is not required**.

The installer contains the packaged game and installs everything required to run it. Ollama can optionally be installed and configured during installation.

### Running from source

Python 3.10+ is required when running Piksel RPG directly from the source code:

```bash
pip install -r requirements.txt
python main.py
```

You can also run the source installer:

```bash
python installer/install.py
```

### Building the Windows executable

Python is required for building the Windows executable and installer.

Install the build dependencies:

```bash
py -m pip install pyinstaller PySide6-Essentials
```

Then build:

```bash
py tools\build_windows.py
```

The installer will be created at:

```text
dist\PikselRPG-Setup.exe
```

## How to Play

1. **Host:** select *Host New Game*, enter a nickname, world name, description, and player count.
2. Choose a connection method and create the game.
3. **Players:** select *Join Game*, enter a nickname, and paste the invite code.
4. Each player creates a character and marks themselves as ready.
5. The host starts the game once everyone is ready.
6. Llama generates the world, map, markers, and opening narration.
7. Each round, living players submit one action. The game engine handles dice rolls and outcomes, while the Game Master describes what happens and updates the world.
8. Dead players can continue watching the game and use the chat.
9. Saved campaigns can be resumed by any participant who has a copy of the save.

## Networking

Piksel RPG supports three main ways of connecting players:

* **LAN/VPN:** for players on the same local network or connected through a VPN such as Tailscale, ZeroTier, or Radmin.
* **Global:** uses a public `bore` TCP tunnel. No port forwarding or public IP is required.
* **Internet:** the host can attempt to open TCP port `47600` automatically using UPnP. Manual port forwarding can also be used.

### How the Global connection works

The Global connection is **not direct P2P**. Both players connect to a public relay server, which forwards the traffic between them.

Think of it like meeting at a shared gateway:

```text
Player B ───────► bore.pub ───────► Host A
                 relay server
```

Neither player needs to open an incoming port on their router.

#### Step by step

1. **The host starts the game.**

   The host's computer opens an outgoing TCP connection to the public `bore.pub` server.

   Outgoing connections normally work through home routers automatically, so the host does not need to configure port forwarding or UPnP.

2. **The tunnel gets a public address.**

   `bore.pub` assigns the host a public TCP address, for example:

   ```text
   bore.pub:41873
   ```

   Data sent to this address is forwarded through the tunnel to the host's already-open connection.

3. **The game creates an invite code.**

   Piksel RPG puts the tunnel address and a random connection token into an invite code such as:

   ```text
   PRPG-...
   ```

   The host sends this code to the other players.

4. **The player enters the code.**

   The joining player pastes the code into Piksel RPG.

   The game reads the tunnel address and token from the code and connects to:

   ```text
   bore.pub:41873
   ```

5. **`bore.pub` connects the two sides.**

   The server detects the new connection and forwards it through the existing tunnel to the host.

   The resulting data path is:

   ```text
   Player B
       │
       ▼
   bore.pub
       │
       ▼
   Host A
   ```

   Game data can now travel in both directions through the relay.

6. **The host verifies the token.**

   The host checks the random token included in the invite code.

   If the token is valid and there is still room in the lobby, the player is allowed to join.

### Why this works without port forwarding

The important part is that **neither computer needs to accept a new incoming connection directly from the Internet**.

Both sides make outgoing connections:

```text
Host ─────► bore.pub
Player ───► bore.pub
```

Home routers generally allow outgoing connections, so this avoids common problems caused by:

* NAT
* no public IP address
* closed incoming ports
* unavailable UPnP
* complicated router configuration

The relay server then connects the two existing connections together.

### What `bore.pub` actually does

The public server is only used as a **TCP relay**.

It does not run the RPG, generate the world, store campaign saves, or act as a central game server.

Conceptually:

```text
Player
   │
   │ game data
   ▼
bore.pub
   │
   │ forwarded bytes
   ▼
Host
```

The actual game logic remains on the host's computer.

This means Piksel RPG does not need its own multiplayer backend or paid server infrastructure for the Global connection.

### Limitations

The Global connection is not pure P2P because traffic passes through `bore.pub`.

This adds some latency, but it is generally not important for a turn-based RPG.

Traffic through the public tunnel is **not encrypted by the tunnel itself**. Access is protected by the random token contained in the invite code.

**Do not publicly share private invite codes.**

If `bore.pub` is unavailable, Global connections will not work until the relay is available again. LAN/VPN and direct Internet connections can still be used.

### Internet connection

The Internet mode attempts to make the host directly reachable by opening TCP port `47600` through UPnP.

If UPnP is unavailable, the port can be forwarded manually in the router.

Public IP detection uses `api.ipify.org` and is optional.

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

The Windows installer produces a standalone version of Piksel RPG.

**Python is not required to install or run the pre-built `.exe`.**

Python is only required if you want to:

* run the game directly from source;
* run the source installer;
* build the Windows executable;
* build the Windows installer.

The installer can optionally install Ollama, download the selected model, and add the required firewall rule through UAC.

Build the installer with:

```bash
py -m pip install pyinstaller PySide6-Essentials
py tools\build_windows.py
```

Output:

```text
dist\PikselRPG-Setup.exe
```

The installer does not require administrator privileges for the basic installation.

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

* AI-generated character roles instead of fixed classes.
* Random world generation.
* Updated Game Master prompt and narration handling.
* Persistent maps that are generated once and then edited during gameplay.
* Multiplayer loading minigame.
* System TTS support on Windows, macOS, and Linux.
* Vote-based game exit system.
* English language support in the game and installer.
* Global Internet connectivity using the `bore` TCP tunnel.
* Local saves for every participant.

## Resource Licenses

* Phosphor Icons — MIT
* Pixelify Sans / Inter — SIL Open Font License
* Logo — custom
* Qt / PySide6 — LGPL
* Ollama — MIT
* Llama models — subject to Meta's applicable license

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

Python 3.10+ is required for development and building from source.
