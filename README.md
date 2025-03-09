# Beszel Agent Installer

Das ist eine Software für Beszel von Hank. Beszel findet ihr hier: https://github.com/henrygd/beszel

## 🔍 Übersicht
Der **Beszel Agent Installer** ist ein Windows-Installationsprogramm, das den Beszel-Agenten auf einem System installiert oder entfernt. Der Installer kann optional eine Firewall-Regel für die Kommunikation erstellen und den Agent als Windows-Dienst mit **NSSM (Non-Sucking Service Manager)** registrieren.

Großes Dankeschön an Alex für das Tutorial zum erstellen der agent.exe. Die Anleitung findet ihr hier: https://blog.ktz.me/using-beszel-to-monitor-windows/amp/
## 🚀 Funktionen
- **Installation des Beszel-Agenten** in `C:\Program Files\beszel-agent` (bzw. `C:\Programme\beszel-agent` auf deutschen Systemen)
- **Optionale Erstellung einer Firewall-Regel** für Port **45876**
- **Registrierung als Windows-Dienst** über **NSSM**
- **Eingabe eines Benutzer-Keys** zur Konfiguration
- **Deinstallation des Beszel-Agenten**
  - Stoppt und entfernt den Dienst
  - Löscht das Installationsverzeichnis
- **Visuelles Installationsfenster mit Fortschrittsanzeige**
- **Log-Datei zur Fehlerverfolgung** (`install.log`)

## 🛠️ Installation & Nutzung

### **1️⃣ Voraussetzungen**
- Windows 10 oder 11 (64-Bit)
- Administratorrechte
- **HINWEIS**: Du wirst wahrschinlich dein Antivirus deaktivieren müssen, da die Anwendung nicht signiert ist!
- Chocolatey (`choco`) muss installiert sein (wird bei Bedarf automatisch installiert)

### **2️⃣ Installation**
1. **Lade die Installer-Dateien herunter** (Installer `.exe` + `agent.exe`).
2. **Starte den Installer (`installer.exe`)** mit **Administratorrechten**.
3. **Folge den Anweisungen** im Installationsassistenten:
   - Lizenzbedingungen akzeptieren
   - Installations- oder Deinstallationsmodus wählen
   - Firewall-Regel erstellen (optional)
   - Public Key eingeben
4. **Klicke auf „Installieren“** und warte, bis der Prozess abgeschlossen ist.
5. **Überprüfe, ob der Dienst läuft:**
   ```sh
   sc query beszelagent
   ```
   Falls `RUNNING` oder `Wird ausgeführt` angezeigt wird, ist die Installation erfolgreich.

### **3️⃣ Deinstallation**
1. **Starte `installer.exe`** mit **Administratorrechten**.
2. **Wähle „Deinstallieren“**.
3. Der Installer:
   - Stoppt und entfernt den **Beszel-Agent-Dienst**.
   - Löscht das Verzeichnis `C:\Program Files\beszel-agent\`.

## 🔧 Fehlerbehebung
Falls der Installer nicht korrekt funktioniert, prüfe die **Log-Datei**:

📄 **Pfad zur Log-Datei:**  
`C:\Program Files\beszel-agent\install.log`

### **1️⃣ Chocolatey wird nicht erkannt**
Falls Chocolatey nicht gefunden wird, versuche die manuelle Installation:
```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force; `
[System.Net.ServicePointManager]::SecurityProtocol = `
[System.Net.ServicePointManager]::SecurityProtocol -bor 3072; `
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
```

### **2️⃣ NSSM-Installation schlägt fehl**
Falls NSSM nicht erkannt wird, installiere es manuell:
```sh
choco install nssm -y
```
Und überprüfe den Installationspfad:
```sh
where nssm
```
Der Pfad sollte `C:\ProgramData\chocolatey\bin\nssm.exe` enthalten.

### **3️⃣ Dienst startet nicht**
Falls der Dienst nicht läuft, versuche:
```sh
sc query beszelagent
net start beszelagent
```
Falls das nicht hilft, entferne und erstelle den Dienst erneut:
```sh
nssm remove beszelagent confirm
nssm install beszelagent "C:\Program Files\beszel-agent\agent.exe"
nssm start beszelagent
```

## 💻 Entwicklung
Falls du Änderungen am Installer vornehmen möchtest:

### **1️⃣ Voraussetzungen**
- Python 3.9 oder höher
- Tkinter (GUI-Bibliothek)
- PyInstaller (zur Erstellung der `.exe`-Datei)

### **2️⃣ Erstellen einer ausführbaren Datei (`installer.exe`)**
Falls du den Installer selbst kompilieren möchtest:
```sh
pyinstaller --onefile --windowed --icon=installer.ico installer.py
```
📌 **Hinweis:** Ersetze `"installer.ico"` durch dein eigenes Icon.

## 📝 Lizenz
Dieses Projekt steht unter der **GNU General Public License version 3**. Siehe die Datei [`LICENSE`](LICENSE) für weitere Details.

## 🤝 Mitwirken
Beiträge sind jederzeit willkommen! Falls du Fehler findest oder neue Funktionen vorschlagen möchtest:
1. **Forke das Repository**.
2. **Erstelle einen Feature-Branch**:
   ```sh
   git checkout -b feature-neue-funktion
   ```
3. **Führe deine Änderungen durch**.
4. **Erstelle einen Pull-Request**.

## 📞 Support
Falls du Fragen oder Probleme hast, erstelle ein **GitHub-Issue** oder kontaktiere mich direkt.

---

📌 **Erstellt von:**  
**Marko Buculovic - VMHOMELAB** 🚀  
