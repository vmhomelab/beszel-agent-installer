# Beszel Agent Installer
![beszelagent](https://github.com/user-attachments/assets/7dc9d747-e43c-4db1-bcbd-3071e703a9c6)

The **Beszel Agent Installer** is a modern Windows installation tool for the Beszel agent by Hank.  
⚠️This project is a third-party tool⚠️
You can find a quick tour of the Beszel Agent here:  
👉 https://youtu.be/6tYfgG63RVo
And the repository of Hank here:
👉 https://github.com/henrygd/beszel

---

# 🔍 Overview

The **Beszel Agent Installer** installs, updates, or removes the Beszel Agent on Windows systems.  
The latest release brings a **complete redesign** of the installer and introduces a brand-new management app:

✔ Modern Windows 11–style UI  
✔ Custom installation directory selection  
✔ Service start-type selection  
✔ Full registry integration  
✔ Completely rebuilt uninstall logic  
✔ **NEW: Beszel Agent Control Center** – a desktop management tool for the agent

---

# 🚀 Features

## 🧩 Installer & Setup
- Modern **Windows 11 Fluent-style interface**
- Choose any **installation directory**
- Select the **service start type**:
  - Automatic  
  - Automatic (Delayed Start)  
  - Manual  
  - Disabled
- Automatic creation & configuration of the Windows service  
- Installation path and version stored in the Windows Registry  
- Detailed progress view and logging  
- Update detection (local version vs. GitHub latest)

---

## 🖥️ NEW – Beszel Agent Control Center

A completely new GUI application to manage the Beszel Agent after installation.

### Features:
- Start, stop, and restart the agent service  
- Real-time service status (Running, Stopped, Disabled, etc.)  
- Display installed and latest GitHub version  
- Update available indicator (no auto-download)  
- Built-in **Log Viewer** (real-time agent logs)  
- Shows installation directory, registry values, configuration  
- Troubleshooting & quick repair tools  

---

# 🛠️ Installation & Usage

## 1️⃣ Requirements
- Windows 10 or Windows 11 (64-bit)
- Administrator privileges
- Antivirus may need to be disabled (unsigned executable)

## 2️⃣ Installation
1. Download the latest `setup.exe`
2. Run it **as Administrator**
3. Choose:
   - Installation directory  
   - Service start type  
4. Enter your **Beszel Public Key**  
5. Click *Install* and wait for completion  
6. Verify the service:
   ```powershell
   sc query beszelagent


### 3️⃣ Uninstallation

Open `setup.exe` again  
Select **Uninstall**  

The uninstaller will:

- Stop & remove the Windows service  
- Delete the installation folder (based on registry entry)

---

### 4️⃣ Updating

Run `setup.exe` and select **Update**  
Installer compares installed version with GitHub  
Automatically updates the agent when necessary

---

# 🔧 Troubleshooting

Logs can be foundin the installation path.

### ❗ Folder does not delete

Windows may lock files.  
The uninstaller attempts deletion twice with retry logic.

### ❗ Service not starting

Try:

```powershell
sc query beszelagent
net start beszelagent
```

If this fails, remove and install the service again:
```sh
nssm remove beszelagent confirm
nssm install beszelagent "C:\Program Files\beszel-agent\agent.exe"
nssm start beszelagent
```

### ❗ Service start type overridden

Group Policies (GPO) on some systems may override service configuration.

### ❗ Chocolatey not installed**
If during the installation chocolatey can't be found nor installed try to manually install it first:
```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force; `
[System.Net.ServicePointManager]::SecurityProtocol = `
[System.Net.ServicePointManager]::SecurityProtocol -bor 3072; `
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
```

### ❗ NSSM installation failed**
If during the installation NSSM can't be found nor installed try to manually install it first:
```sh
choco install nssm -y
```
Check the installation path:
```sh
where nssm
```
Path should be something like `C:\ProgramData\chocolatey\bin\nssm.exe`.

### **1️⃣ Developement**
- Python 3.10+
- Tkinter
- PyInstaller

### **2️⃣ Build the installer (`Setup.exe`)**
Falls du den Installer selbst kompilieren möchtest:
```sh
py -m PyInstaller --onefile --noconsole --name Setup --icon=beszelagent.ico  --add-data "BeszelAgentControl.exe;." -F installer.py
```

## 📝 License
This project is licensed under **GNU GPLv3**. See the [`LICENSE`](LICENSE) file for details.

## 🤝 Contributing
Contributions are welcome!
1. **Fork the repository**.
2. **Create a feature branch:**:
   ```sh
   git checkout -b feature-neue-funktion
   ```
3. **Commit your changes**.
4. **Open a Pull Request**.

## 📞 Support
For questions or issues, open a GitHub Issue or contact me directly.

---

📌 **Created by:**  
**Marko Buculovic - VMHOMELAB** 🚀  
## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=vmhomelab/beszel-agent-installer&type=Date)](https://www.star-history.com/#vmhomelab/beszel-agent-installer&Date)
