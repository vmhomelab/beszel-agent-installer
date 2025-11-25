import os
import subprocess
import shutil
import requests
import zipfile
import time
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
import threading
import ctypes

base_path = os.path.dirname(os.path.abspath(__file__))
icon_path = os.path.join(base_path, "beszelagent.ico")

# ---------------- THEME (Windows 11 Style) ---------------- #

THEME = {
    "light": {
        "bg": "#f3f3f3",
        "card": "#ffffff",
        "border": "#d4d4d4",
        "text": "#111827",
        "muted": "#555555",
        "accent": "#2563eb",
    },
    "dark": {
        "bg": "#1f1f1f",
        "card": "#2b2b2b",
        "border": "#3a3a3a",
        "text": "#e5e5e5",
        "muted": "#a3a3a3",
        "accent": "#3b82f6",
    }
}

current_theme = "dark"
style: ttk.Style | None = None


def apply_theme(root: tk.Tk):
    """Apply Windows 11-like theme to the installer window."""
    global style, current_theme
    th = THEME[current_theme]

    if style is None:
        style = ttk.Style()

    # Basis-Theme
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    root.configure(bg=th["bg"])

    # Frames
    style.configure("Main.TFrame", background=th["bg"])
    style.configure(
        "Card.TFrame",
        background=th["card"],
        borderwidth=1,
        relief="solid"
    )

    # Labels
    style.configure("Header.TLabel", background=th["bg"], foreground=th["text"], font=("Segoe UI Semibold", 16))
    style.configure("SubHeader.TLabel", background=th["bg"], foreground=th["muted"], font=("Segoe UI", 10))
    style.configure("CardTitle.TLabel", background=th["card"], foreground=th["text"], font=("Segoe UI Semibold", 12))
    style.configure("CardText.TLabel", background=th["card"], foreground=th["text"], font=("Segoe UI", 10))
    style.configure("TLabel", background=th["card"], foreground=th["text"], font=("Segoe UI", 10))

    # Buttons
    style.configure(
        "Accent.TButton",
        background=th["accent"],
        foreground="#ffffff",
        font=("Segoe UI Semibold", 10),
        padding=(16, 6)
    )
    style.map(
        "Accent.TButton",
        background=[("active", th["accent"])],
        foreground=[("active", "#e5e5e5")]
    )

    style.configure(
        "Ghost.TButton",
        background=th["card"],
        foreground=th["text"],
        font=("Segoe UI", 10),
        padding=(14, 5)
    )
    style.map(
        "Ghost.TButton",
        background=[("active", th["border"])],
    )

    # Progressbar green style
    style.configure(
        "green.Horizontal.TProgressbar",
        troughcolor=THEME[current_theme]["card"],
        background="#16a34a",  # Green-600 (Windows 11-like)
        lightcolor="#16a34a",
        darkcolor="#15803d",
        bordercolor=THEME[current_theme]["border"]
    )

def toggle_theme(root: tk.Tk):
    global current_theme
    current_theme = "dark" if current_theme == "light" else "light"
    apply_theme(root)


# ---------------- INSTALLER APP ---------------- #
def ensure_admin():
    """
    Relaunch the script as admin if not already elevated.
    """
    try:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
    except:
        is_admin = False

    if not is_admin:
        # Re-run with admin rights
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable,
            " ".join([sys.argv[0]] + sys.argv[1:]),
            None, 1
        )
        sys.exit()

# Call immediately at startup
ensure_admin()
class InstallerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Beszel Agent – Installer")
        self.root.minsize(900, 600)

        # Default font
        self.root.option_add("*Font", ("Segoe UI", 10))

        # State / Logic
        self.current_page = 0
        self.user_choice = tk.StringVar(value="install")
        self.firewall_choice = tk.StringVar(value="yes")
        self.user_key = tk.StringVar()
        self.license_var = tk.BooleanVar()
        self.env_vars = []  # Store environment variables
        self.service_start_type = tk.StringVar(value="auto")

        self.install_path = os.path.join(
            os.environ.get("ProgramW6432", os.environ.get("ProgramFiles", "C:\\Program Files")),
            "beszel-agent"
        ) if os.path.exists(os.environ.get("ProgramW6432", os.environ.get("ProgramFiles", "C:\\Program Files"))) else os.path.join("C:\\Programme", "beszel-agent")

        self.custom_install_path = tk.StringVar(value=self.install_path)
        self.downloads_folder = os.path.join(os.environ["USERPROFILE"], "Downloads")

        self.log_file = os.path.join(self.custom_install_path.get(), "install.log")
        self.control_center_source = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "BeszelAgentControl.exe"
        )

        self.user_key_entry = None
        self.installation_status = ""

        # Layout: outer frame with header + card + nav
        self.outer = ttk.Frame(self.root, style="Main.TFrame", padding=20)
        self.outer.pack(fill="both", expand=True)

        # Header (Title + Subtitle + Theme Switch)
        header = ttk.Frame(self.outer, style="Main.TFrame")
        header.pack(fill="x", pady=(0, 15))

        header_left = ttk.Frame(header, style="Main.TFrame")
        header_left.pack(side="left", fill="x", expand=True)

        ttk.Label(
            header_left,
            text="Beszel Agent Installer",
            style="Header.TLabel"
        ).pack(anchor="w")

        ttk.Label(
            header_left,
            text="Install, update or remove the Beszel Agent service on Windows.",
            style="SubHeader.TLabel"
        ).pack(anchor="w", pady=(2, 0))

        header_right = ttk.Frame(header, style="Main.TFrame")
        header_right.pack(side="right")

        theme_btn = ttk.Button(
            header_right,
            text="Toggle dark mode",
            style="Ghost.TButton",
            command=lambda: toggle_theme(self.root)
        )
        theme_btn.pack(anchor="e")

        # Card for page content
        self.frame = ttk.Frame(self.outer, style="Card.TFrame", padding=20)
        self.frame.pack(fill="both", expand=True)

        # Navigation bar
        self.nav_frame = ttk.Frame(self.outer, style="Main.TFrame")
        self.nav_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(15, 0))

        self.back_button = ttk.Button(self.nav_frame, text="Back", style="Ghost.TButton", command=self.prev_page)
        self.back_button.pack(side=tk.LEFT, padx=10, pady=10)

        self.next_button = ttk.Button(self.nav_frame, text="Next", style="Accent.TButton", command=self.next_page)
        self.next_button.pack(side=tk.RIGHT, padx=10, pady=10)

        self.cancel_button = ttk.Button(self.nav_frame, text="Cancel", style="Ghost.TButton", command=root.quit)
        self.cancel_button.pack(side=tk.RIGHT, padx=10, pady=10)

        # Ordered pages
        self.pages = [
            self.page_welcome,
            self.page_license,
            self.page_choice,
            self.page_key,
            self.page_service_settings,
            self.page_env_vars,
            self.page_overview,
            self.page_installation,
            self.page_uninstall,
            self.page_update,
            self.page_summary
        ]

        self.progress = None
        self.install_log_text = None
        self.uninstall_log_text = None
        self.log_text = None

        # Show first page
        self.pages[self.current_page]()

    # ---------- Utility ---------- #

    def log(self, message):
        os.makedirs(self.install_path, exist_ok=True)
        with open(self.log_file, "a", encoding="utf-8", errors="ignore") as log:
            log.write(message + "\n")
        print(message)

    def clear_frame(self):
        for widget in self.frame.winfo_children():
            widget.destroy()

    def show_navigation(self, back=True, next=True, cancel=True):
        self.back_button.pack_forget()
        self.next_button.pack_forget()
        self.cancel_button.pack_forget()

        if back:
            self.back_button.pack(side=tk.LEFT, padx=10, pady=10)
        if cancel:
            self.cancel_button.pack(side=tk.RIGHT, padx=10, pady=10)
        if next:
            self.next_button.pack(side=tk.RIGHT, padx=10, pady=10)

    # ---------- Navigation ---------- #

    def next_page(self):
        # License check
        if self.current_page == 1 and not self.license_var.get():
            messagebox.showwarning("License agreement", "Please accept the license agreement to continue.")
            return

        # Choice page
        if self.current_page == 2:
            self.process_choice()
            return

        # Public key check on key page (only for install)
        if self.current_page == 4 and self.user_choice.get() == "install":
            key = self.user_key.get().strip()
            if not key:
                messagebox.showwarning("Public key missing", "Please enter a valid public key.")
                return

        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
            self.pages[self.current_page]()

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.pages[self.current_page]()

    # ---------- Pages ---------- #

    def page_welcome(self):
        self.clear_frame()
        ttk.Label(self.frame, text="Welcome to the Beszel Agent Setup", style="CardTitle.TLabel").pack(anchor="w")
        ttk.Label(
            self.frame,
            text="This wizard will guide you through the installation, update or removal of the Beszel Agent service.",
            style="CardText.TLabel",
            wraplength=640,
            justify="left"
        ).pack(anchor="w", pady=(8, 0))

        self.next_button.config(text="Next", state=tk.NORMAL)
        self.show_navigation(back=False, next=True, cancel=True)

    def page_license(self):
        self.clear_frame()
        ttk.Label(self.frame, text="License agreement", style="CardTitle.TLabel").pack(anchor="w", pady=(0, 8))

        license_text = scrolledtext.ScrolledText(self.frame, wrap=tk.WORD, height=12, width=80)
        license_text.insert(tk.END, self._license_text())
        license_text.config(state=tk.DISABLED)
        license_text.pack(fill="both", expand=True, pady=(0, 10))

        ttk.Checkbutton(
            self.frame,
            text="I have read and accept the license agreement",
            variable=self.license_var,
            command=self.check_license
        ).pack(anchor="w", pady=(4, 0))

        self.next_button.config(state=tk.DISABLED, text="Next")
        self.show_navigation(back=True, next=True, cancel=True)

    def _license_text(self):
        # Original GPLv3 text from your file, shortened in code for readability
        return (
            """Preamble\n"
            "The GNU General Public License is a free, copyleft license for software and other kinds of works.\n\n"
            "...\n\n"
            "The licenses for most software and other practical works are designed to take away your freedom to share and change the works. By contrast, the GNU General Public License is intended to guarantee your freedom to share and change all versions of a program–to make sure it remains free software for all its users. We, the Free Software Foundation, use the GNU General Public License for most of our software; it applies also to any other work released this way by its authors. You can apply it to your programs, too.

            When we speak of free software, we are referring to freedom, not price. Our General Public Licenses are designed to make sure that you have the freedom to distribute copies of free software (and charge for them if you wish), that you receive source code or can get it if you want it, that you can change the software or use pieces of it in new free programs, and that you know you can do these things.

            To protect your rights, we need to prevent others from denying you these rights or asking you to surrender the rights. Therefore, you have certain responsibilities if you distribute copies of the software, or if you modify it: responsibilities to respect the freedom of others.

            For example, if you distribute copies of such a program, whether gratis or for a fee, you must pass on to the recipients the same freedoms that you received. You must make sure that they, too, receive or can get the source code. And you must show them these terms so they know their rights.

            Developers that use the GNU GPL protect your rights with two steps: (1) assert copyright on the software, and (2) offer you this License giving you legal permission to copy, distribute and/or modify it.

            For the developers’ and authors’ protection, the GPL clearly explains that there is no warranty for this free software. For both users’ and authors’ sake, the GPL requires that modified versions be marked as changed, so that their problems will not be attributed erroneously to authors of previous versions.

            Some devices are designed to deny users access to install or run modified versions of the software inside them, although the manufacturer can do so. This is fundamentally incompatible with the aim of protecting users’ freedom to change the software. The systematic pattern of such abuse occurs in the area of products for individuals to use, which is precisely where it is most unacceptable. Therefore, we have designed this version of the GPL to prohibit the practice for those products. If such problems arise substantially in other domains, we stand ready to extend this provision to those domains in future versions of the GPL, as needed to protect the freedom of users.

            Finally, every program is threatened constantly by software patents. States should not allow patents to restrict development and use of software on general-purpose computers, but in those that do, we wish to avoid the special danger that patents applied to a free program could make it effectively proprietary. To prevent this, the GPL assures that patents cannot be used to render the program non-free.

            The precise terms and conditions for copying, distribution and modification follow.

            TERMS AND CONDITIONS
            0. Definitions.

            “This License” refers to version 3 of the GNU General Public License.

            “Copyright” also means copyright-like laws that apply to other kinds of works, such as semiconductor masks.

            “The Program” refers to any copyrightable work licensed under this License. Each licensee is addressed as “you”. “Licensees” and “recipients” may be individuals or organizations.

            To “modify” a work means to copy from or adapt all or part of the work in a fashion requiring copyright permission, other than the making of an exact copy. The resulting work is called a “modified version” of the earlier work or a work “based on” the earlier work.

            A “covered work” means either the unmodified Program or a work based on the Program.

            To “propagate” a work means to do anything with it that, without permission, would make you directly or secondarily liable for infringement under applicable copyright law, except executing it on a computer or modifying a private copy. Propagation includes copying, distribution (with or without modification), making available to the public, and in some countries other activities as well.

            To “convey” a work means any kind of propagation that enables other parties to make or receive copies. Mere interaction with a user through a computer network, with no transfer of a copy, is not conveying.

            An interactive user interface displays “Appropriate Legal Notices” to the extent that it includes a convenient and prominently visible feature that (1) displays an appropriate copyright notice, and (2) tells the user that there is no warranty for the work (except to the extent that warranties are provided), that licensees may convey the work under this License, and how to view a copy of this License. If the interface presents a list of user commands or options, such as a menu, a prominent item in the list meets this criterion.

            1. Source Code.

            The “source code” for a work means the preferred form of the work for making modifications to it. “Object code” means any non-source form of a work.

            A “Standard Interface” means an interface that either is an official standard defined by a recognized standards body, or, in the case of interfaces specified for a particular programming language, one that is widely used among developers working in that language.

            The “System Libraries” of an executable work include anything, other than the work as a whole, that (a) is included in the normal form of packaging a Major Component, but which is not part of that Major Component, and (b) serves only to enable use of the work with that Major Component, or to implement a Standard Interface for which an implementation is available to the public in source code form. A “Major Component”, in this context, means a major essential component (kernel, window system, and so on) of the specific operating system (if any) on which the executable work runs, or a compiler used to produce the work, or an object code interpreter used to run it.

            The “Corresponding Source” for a work in object code form means all the source code needed to generate, install, and (for an executable work) run the object code and to modify the work, including scripts to control those activities. However, it does not include the work’s System Libraries, or general-purpose tools or generally available free programs which are used unmodified in performing those activities but which are not part of the work. For example, Corresponding Source includes interface definition files associated with source files for the work, and the source code for shared libraries and dynamically linked subprograms that the work is specifically designed to require, such as by intimate data communication or control flow between those subprograms and other parts of the work.

            The Corresponding Source need not include anything that users can regenerate automatically from other parts of the Corresponding Source.

            The Corresponding Source for a work in source code form is that same work.

            2. Basic Permissions.

            All rights granted under this License are granted for the term of copyright on the Program, and are irrevocable provided the stated conditions are met. This License explicitly affirms your unlimited permission to run the unmodified Program. The output from running a covered work is covered by this License only if the output, given its content, constitutes a covered work. This License acknowledges your rights of fair use or other equivalent, as provided by copyright law.

            You may make, run and propagate covered works that you do not convey, without conditions so long as your license otherwise remains in force. You may convey covered works to others for the sole purpose of having them make modifications exclusively for you, or provide you with facilities for running those works, provided that you comply with the terms of this License in conveying all material for which you do not control copyright. Those thus making or running the covered works for you must do so exclusively on your behalf, under your direction and control, on terms that prohibit them from making any copies of your copyrighted material outside their relationship with you.

            Conveying under any other circumstances is permitted solely under the conditions stated below. Sublicensing is not allowed; section 10 makes it unnecessary.

            3. Protecting Users’ Legal Rights From Anti-Circumvention Law.

            No covered work shall be deemed part of an effective technological measure under any applicable law fulfilling obligations under article 11 of the WIPO copyright treaty adopted on 20 December 1996, or similar laws prohibiting or restricting circumvention of such measures.

            When you convey a covered work, you waive any legal power to forbid circumvention of technological measures to the extent such circumvention is effected by exercising rights under this License with respect to the covered work, and you disclaim any intention to limit operation or modification of the work as a means of enforcing, against the work’s users, your or third parties’ legal rights to forbid circumvention of technological measures.

            4. Conveying Verbatim Copies.

            You may convey verbatim copies of the Program’s source code as you receive it, in any medium, provided that you conspicuously and appropriately publish on each copy an appropriate copyright notice; keep intact all notices stating that this License and any non-permissive terms added in accord with section 7 apply to the code; keep intact all notices of the absence of any warranty; and give all recipients a copy of this License along with the Program.

            You may charge any price or no price for each copy that you convey, and you may offer support or warranty protection for a fee.

            5. Conveying Modified Source Versions.

            You may convey a work based on the Program, or the modifications to produce it from the Program, in the form of source code under the terms of section 4, provided that you also meet all of these conditions:

            a) The work must carry prominent notices stating that you modified it, and giving a relevant date.
            b) The work must carry prominent notices stating that it is released under this License and any conditions added under section 7. This requirement modifies the requirement in section 4 to “keep intact all notices”.
            c) You must license the entire work, as a whole, under this License to anyone who comes into possession of a copy. This License will therefore apply, along with any applicable section 7 additional terms, to the whole of the work, and all its parts, regardless of how they are packaged. This License gives no permission to license the work in any other way, but it does not invalidate such permission if you have separately received it.
            d) If the work has interactive user interfaces, each must display Appropriate Legal Notices; however, if the Program has interactive interfaces that do not display Appropriate Legal Notices, your work need not make them do so.
            A compilation of a covered work with other separate and independent works, which are not by their nature extensions of the covered work, and which are not combined with it such as to form a larger program, in or on a volume of a storage or distribution medium, is called an “aggregate” if the compilation and its resulting copyright are not used to limit the access or legal rights of the compilation’s users beyond what the individual works permit. Inclusion of a covered work in an aggregate does not cause this License to apply to the other parts of the aggregate.

            6. Conveying Non-Source Forms.

            You may convey a covered work in object code form under the terms of sections 4 and 5, provided that you also convey the machine-readable Corresponding Source under the terms of this License, in one of these ways:

            a) Convey the object code in, or embodied in, a physical product (including a physical distribution medium), accompanied by the Corresponding Source fixed on a durable physical medium customarily used for software interchange.
            b) Convey the object code in, or embodied in, a physical product (including a physical distribution medium), accompanied by a written offer, valid for at least three years and valid for as long as you offer spare parts or customer support for that product model, to give anyone who possesses the object code either (1) a copy of the Corresponding Source for all the software in the product that is covered by this License, on a durable physical medium customarily used for software interchange, for a price no more than your reasonable cost of physically performing this conveying of source, or (2) access to copy the Corresponding Source from a network server at no charge.
            c) Convey individual copies of the object code with a copy of the written offer to provide the Corresponding Source. This alternative is allowed only occasionally and noncommercially, and only if you received the object code with such an offer, in accord with subsection 6b.
            d) Convey the object code by offering access from a designated place (gratis or for a charge), and offer equivalent access to the Corresponding Source in the same way through the same place at no further charge. You need not require recipients to copy the Corresponding Source along with the object code. If the place to copy the object code is a network server, the Corresponding Source may be on a different server (operated by you or a third party) that supports equivalent copying facilities, provided you maintain clear directions next to the object code saying where to find the Corresponding Source. Regardless of what server hosts the Corresponding Source, you remain obligated to ensure that it is available for as long as needed to satisfy these requirements.
            e) Convey the object code using peer-to-peer transmission, provided you inform other peers where the object code and Corresponding Source of the work are being offered to the general public at no charge under subsection 6d.
            A separable portion of the object code, whose source code is excluded from the Corresponding Source as a System Library, need not be included in conveying the object code work.

            A “User Product” is either (1) a “consumer product”, which means any tangible personal property which is normally used for personal, family, or household purposes, or (2) anything designed or sold for incorporation into a dwelling. In determining whether a product is a consumer product, doubtful cases shall be resolved in favor of coverage. For a particular product received by a particular user, “normally used” refers to a typical or common use of that class of product, regardless of the status of the particular user or of the way in which the particular user actually uses, or expects or is expected to use, the product. A product is a consumer product regardless of whether the product has substantial commercial, industrial or non-consumer uses, unless such uses represent the only significant mode of use of the product.

            “Installation Information” for a User Product means any methods, procedures, authorization keys, or other information required to install and execute modified versions of a covered work in that User Product from a modified version of its Corresponding Source. The information must suffice to ensure that the continued functioning of the modified object code is in no case prevented or interfered with solely because modification has been made.

            If you convey an object code work under this section in, or with, or specifically for use in, a User Product, and the conveying occurs as part of a transaction in which the right of possession and use of the User Product is transferred to the recipient in perpetuity or for a fixed term (regardless of how the transaction is characterized), the Corresponding Source conveyed under this section must be accompanied by the Installation Information. But this requirement does not apply if neither you nor any third party retains the ability to install modified object code on the User Product (for example, the work has been installed in ROM).

            The requirement to provide Installation Information does not include a requirement to continue to provide support service, warranty, or updates for a work that has been modified or installed by the recipient, or for the User Product in which it has been modified or installed. Access to a network may be denied when the modification itself materially and adversely affects the operation of the network or violates the rules and protocols for communication across the network.

            Corresponding Source conveyed, and Installation Information provided, in accord with this section must be in a format that is publicly documented (and with an implementation available to the public in source code form), and must require no special password or key for unpacking, reading or copying.

            7. Additional Terms.

            “Additional permissions” are terms that supplement the terms of this License by making exceptions from one or more of its conditions. Additional permissions that are applicable to the entire Program shall be treated as though they were included in this License, to the extent that they are valid under applicable law. If additional permissions apply only to part of the Program, that part may be used separately under those permissions, but the entire Program remains governed by this License without regard to the additional permissions.

            When you convey a copy of a covered work, you may at your option remove any additional permissions from that copy, or from any part of it. (Additional permissions may be written to require their own removal in certain cases when you modify the work.) You may place additional permissions on material, added by you to a covered work, for which you have or can give appropriate copyright permission.

            Notwithstanding any other provision of this License, for material you add to a covered work, you may (if authorized by the copyright holders of that material) supplement the terms of this License with terms:

            a) Disclaiming warranty or limiting liability differently from the terms of sections 15 and 16 of this License; or
            b) Requiring preservation of specified reasonable legal notices or author attributions in that material or in the Appropriate Legal Notices displayed by works containing it; or
            c) Prohibiting misrepresentation of the origin of that material, or requiring that modified versions of such material be marked in reasonable ways as different from the original version; or
            d) Limiting the use for publicity purposes of names of licensors or authors of the material; or
            e) Declining to grant rights under trademark law for use of some trade names, trademarks, or service marks; or
            f) Requiring indemnification of licensors and authors of that material by anyone who conveys the material (or modified versions of it) with contractual assumptions of liability to the recipient, for any liability that these contractual assumptions directly impose on those licensors and authors.
            All other non-permissive additional terms are considered “further restrictions” within the meaning of section 10. If the Program as you received it, or any part of it, contains a notice stating that it is governed by this License along with a term that is a further restriction, you may remove that term. If a license document contains a further restriction but permits relicensing or conveying under this License, you may add to a covered work material governed by the terms of that license document, provided that the further restriction does not survive such relicensing or conveying.

            If you add terms to a covered work in accord with this section, you must place, in the relevant source files, a statement of the additional terms that apply to those files, or a notice indicating where to find the applicable terms.

            Additional terms, permissive or non-permissive, may be stated in the form of a separately written license, or stated as exceptions; the above requirements apply either way.

            8. Termination.

            You may not propagate or modify a covered work except as expressly provided under this License. Any attempt otherwise to propagate or modify it is void, and will automatically terminate your rights under this License (including any patent licenses granted under the third paragraph of section 11).

            However, if you cease all violation of this License, then your license from a particular copyright holder is reinstated (a) provisionally, unless and until the copyright holder explicitly and finally terminates your license, and (b) permanently, if the copyright holder fails to notify you of the violation by some reasonable means prior to 60 days after the cessation.

            Moreover, your license from a particular copyright holder is reinstated permanently if the copyright holder notifies you of the violation by some reasonable means, this is the first time you have received notice of violation of this License (for any work) from that copyright holder, and you cure the violation prior to 30 days after your receipt of the notice.

            Termination of your rights under this section does not terminate the licenses of parties who have received copies or rights from you under this License. If your rights have been terminated and not permanently reinstated, you do not qualify to receive new licenses for the same material under section 10.

            9. Acceptance Not Required for Having Copies.

            You are not required to accept this License in order to receive or run a copy of the Program. Ancillary propagation of a covered work occurring solely as a consequence of using peer-to-peer transmission to receive a copy likewise does not require acceptance. However, nothing other than this License grants you permission to propagate or modify any covered work. These actions infringe copyright if you do not accept this License. Therefore, by modifying or propagating a covered work, you indicate your acceptance of this License to do so.

            10. Automatic Licensing of Downstream Recipients.

            Each time you convey a covered work, the recipient automatically receives a license from the original licensors, to run, modify and propagate that work, subject to this License. You are not responsible for enforcing compliance by third parties with this License.

            An “entity transaction” is a transaction transferring control of an organization, or substantially all assets of one, or subdividing an organization, or merging organizations. If propagation of a covered work results from an entity transaction, each party to that transaction who receives a copy of the work also receives whatever licenses to the work the party’s predecessor in interest had or could give under the previous paragraph, plus a right to possession of the Corresponding Source of the work from the predecessor in interest, if the predecessor has it or can get it with reasonable efforts.

            You may not impose any further restrictions on the exercise of the rights granted or affirmed under this License. For example, you may not impose a license fee, royalty, or other charge for exercise of rights granted under this License, and you may not initiate litigation (including a cross-claim or counterclaim in a lawsuit) alleging that any patent claim is infringed by making, using, selling, offering for sale, or importing the Program or any portion of it.

            11. Patents.

            A “contributor” is a copyright holder who authorizes use under this License of the Program or a work on which the Program is based. The work thus licensed is called the contributor’s “contributor version”.

            A contributor’s “essential patent claims” are all patent claims owned or controlled by the contributor, whether already acquired or hereafter acquired, that would be infringed by some manner, permitted by this License, of making, using, or selling its contributor version, but do not include claims that would be infringed only as a consequence of further modification of the contributor version. For purposes of this definition, “control” includes the right to grant patent sublicenses in a manner consistent with the requirements of this License.

            Each contributor grants you a non-exclusive, worldwide, royalty-free patent license under the contributor’s essential patent claims, to make, use, sell, offer for sale, import and otherwise run, modify and propagate the contents of its contributor version.

            In the following three paragraphs, a “patent license” is any express agreement or commitment, however denominated, not to enforce a patent (such as an express permission to practice a patent or covenant not to sue for patent infringement). To “grant” such a patent license to a party means to make such an agreement or commitment not to enforce a patent against the party.

            If you convey a covered work, knowingly relying on a patent license, and the Corresponding Source of the work is not available for anyone to copy, free of charge and under the terms of this License, through a publicly available network server or other readily accessible means, then you must either (1) cause the Corresponding Source to be so available, or (2) arrange to deprive yourself of the benefit of the patent license for this particular work, or (3) arrange, in a manner consistent with the requirements of this License, to extend the patent license to downstream recipients. “Knowingly relying” means you have actual knowledge that, but for the patent license, your conveying the covered work in a country, or your recipient’s use of the covered work in a country, would infringe one or more identifiable patents in that country that you have reason to believe are valid.

            If, pursuant to or in connection with a single transaction or arrangement, you convey, or propagate by procuring conveyance of, a covered work, and grant a patent license to some of the parties receiving the covered work authorizing them to use, propagate, modify or convey a specific copy of the covered work, then the patent license you grant is automatically extended to all recipients of the covered work and works based on it.

            A patent license is “discriminatory” if it does not include within the scope of its coverage, prohibits the exercise of, or is conditioned on the non-exercise of one or more of the rights that are specifically granted under this License. You may not convey a covered work if you are a party to an arrangement with a third party that is in the business of distributing software, under which you make payment to the third party based on the extent of your activity of conveying the work, and under which the third party grants, to any of the parties who would receive the covered work from you, a discriminatory patent license (a) in connection with copies of the covered work conveyed by you (or copies made from those copies), or (b) primarily for and in connection with specific products or compilations that contain the covered work, unless you entered into that arrangement, or that patent license was granted, prior to 28 March 2007.

            Nothing in this License shall be construed as excluding or limiting any implied license or other defenses to infringement that may otherwise be available to you under applicable patent law.

            12. No Surrender of Others’ Freedom.

            If conditions are imposed on you (whether by court order, agreement or otherwise) that contradict the conditions of this License, they do not excuse you from the conditions of this License. If you cannot convey a covered work so as to satisfy simultaneously your obligations under this License and any other pertinent obligations, then as a consequence you may not convey it at all. For example, if you agree to terms that obligate you to collect a royalty for further conveying from those to whom you convey the Program, the only way you could satisfy both those terms and this License would be to refrain entirely from conveying the Program.

            13. Use with the GNU Affero General Public License.

            Notwithstanding any other provision of this License, you have permission to link or combine any covered work with a work licensed under version 3 of the GNU Affero General Public License into a single combined work, and to convey the resulting work. The terms of this License will continue to apply to the part which is the covered work, but the special requirements of the GNU Affero General Public License, section 13, concerning interaction through a network will apply to the combination as such.

            14. Revised Versions of this License.

            The Free Software Foundation may publish revised and/or new versions of the GNU General Public License from time to time. Such new versions will be similar in spirit to the present version, but may differ in detail to address new problems or concerns.

            Each version is given a distinguishing version number. If the Program specifies that a certain numbered version of the GNU General Public License “or any later version” applies to it, you have the option of following the terms and conditions either of that numbered version or of any later version published by the Free Software Foundation. If the Program does not specify a version number of the GNU General Public License, you may choose any version ever published by the Free Software Foundation.

            If the Program specifies that a proxy can decide which future versions of the GNU General Public License can be used, that proxy’s public statement of acceptance of a version permanently authorizes you to choose that version for the Program.

            Later license versions may give you additional or different permissions. However, no additional obligations are imposed on any author or copyright holder as a result of your choosing to follow a later version.

            15. Disclaimer of Warranty.

            THERE IS NO WARRANTY FOR THE PROGRAM, TO THE EXTENT PERMITTED BY APPLICABLE LAW. EXCEPT WHEN OTHERWISE STATED IN WRITING THE COPYRIGHT HOLDERS AND/OR OTHER PARTIES PROVIDE THE PROGRAM “AS IS” WITHOUT WARRANTY OF ANY KIND, EITHER EXPRESSED OR IMPLIED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE. THE ENTIRE RISK AS TO THE QUALITY AND PERFORMANCE OF THE PROGRAM IS WITH YOU. SHOULD THE PROGRAM PROVE DEFECTIVE, YOU ASSUME THE COST OF ALL NECESSARY SERVICING, REPAIR OR CORRECTION.

            16. Limitation of Liability.

            IN NO EVENT UNLESS REQUIRED BY APPLICABLE LAW OR AGREED TO IN WRITING WILL ANY COPYRIGHT HOLDER, OR ANY OTHER PARTY WHO MODIFIES AND/OR CONVEYS THE PROGRAM AS PERMITTED ABOVE, BE LIABLE TO YOU FOR DAMAGES, INCLUDING ANY GENERAL, SPECIAL, INCIDENTAL OR CONSEQUENTIAL DAMAGES ARISING OUT OF THE USE OR INABILITY TO USE THE PROGRAM (INCLUDING BUT NOT LIMITED TO LOSS OF DATA OR DATA BEING RENDERED INACCURATE OR LOSSES SUSTAINED BY YOU OR THIRD PARTIES OR A FAILURE OF THE PROGRAM TO OPERATE WITH ANY OTHER PROGRAMS), EVEN IF SUCH HOLDER OR OTHER PARTY HAS BEEN ADVISED OF THE POSSIBILITY OF SUCH DAMAGES.

            17. Interpretation of Sections 15 and 16.

            If the disclaimer of warranty and limitation of liability provided above cannot be given local legal effect according to their terms, reviewing courts shall apply local law that most closely approximates an absolute waiver of all civil liability in connection with the Program, unless a warranty or assumption of liability accompanies a copy of the Program in return for a fee.

            END OF TERMS AND CONDITIONS

            How to Apply These Terms to Your New Programs

            If you develop a new program, and you want it to be of the greatest possible use to the public, the best way to achieve this is to make it free software which everyone can redistribute and change under these terms.

            To do so, attach the following notices to the program. It is safest to attach them to the start of each source file to most effectively state the exclusion of warranty; and each file should have at least the “copyright” line and a pointer to where the full notice is found.

            <one line to give the program’s name and a brief idea of what it does.> Copyright (C) <year> <name of author> This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version. This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details. You should have received a copy of the GNU General Public License along with this program. If not, see <http://www.gnu.org/licenses/>.

            Also add information on how to contact you by electronic and paper mail.
            If the program does terminal interaction, make it output a short notice like this when it starts in an interactive mode:

            <program> Copyright (C) <year> <name of author> This program comes with ABSOLUTELY NO WARRANTY; for details type `show w’. This is free software, and you are welcome to redistribute it under certain conditions; type `show c’ for details.

            The hypothetical commands `show w’ and `show c’ should show the appropriate parts of the General Public License. Of course, your program’s commands might be different; for a GUI interface, you would use an “about box”.

            You should also get your employer (if you work as a programmer) or school, if any, to sign a “copyright disclaimer” for the program, if necessary. For more information on this, and how to apply and follow the GNU GPL, see <http://www.gnu.org/licenses/>.

            The GNU General Public License does not permit incorporating your program into proprietary programs. If your program is a subroutine library, you may consider it more useful to permit linking proprietary applications with the library. If this is what you want to do, use the GNU Lesser General Public License instead of this License. But first, please read <http://www.gnu.org/philosophy/why-not-lgpl.html>"""
        )

    def check_license(self):
        self.next_button.config(state=tk.NORMAL if self.license_var.get() else tk.DISABLED)

    def page_choice(self):
        self.clear_frame()
        ttk.Label(self.frame, text="What do you want to do?", style="CardTitle.TLabel").pack(anchor="w", pady=(0, 10))

        self.user_choice.set("install")

        ttk.Radiobutton(
            self.frame,
            text="Install Beszel Agent",
            variable=self.user_choice,
            value="install"
        ).pack(anchor="w", pady=2)

        ttk.Radiobutton(
            self.frame,
            text="Uninstall Beszel Agent",
            variable=self.user_choice,
            value="uninstall"
        ).pack(anchor="w", pady=2)

        ttk.Radiobutton(
            self.frame,
            text="Update existing Beszel Agent",
            variable=self.user_choice,
            value="update"
        ).pack(anchor="w", pady=2)

        self.show_navigation(back=True, next=True, cancel=True)

    def process_choice(self):
        choice = self.user_choice.get()

        if choice == "install":
            self.current_page = self.pages.index(self.page_key)
            self.page_key()
        elif choice == "uninstall":
            self.current_page = self.pages.index(self.page_uninstall)
            self.page_uninstall()
        elif choice == "update":
            self.current_page = self.pages.index(self.page_update)
            self.page_update()

    def page_key(self):
        self.clear_frame()
        ttk.Label(self.frame, text="Public key", style="CardTitle.TLabel").pack(anchor="w")

        ttk.Label(
            self.frame,
            text="Please enter your Beszel public key to link this agent to your Beszel instance.",
            style="CardText.TLabel",
            wraplength=640,
            justify="left"
        ).pack(anchor="w", pady=(6, 10))

        entry = ttk.Entry(self.frame, textvariable=self.user_key, width=60)
        entry.pack(anchor="w", pady=(0, 5))
        entry.focus()

        def on_key_change(*_):
            key = self.user_key.get().strip()
            self.next_button.config(state=tk.NORMAL if key else tk.DISABLED)

        self.user_key.trace_add("write", on_key_change)

        self.next_button.config(state=tk.DISABLED, text="Next")
        self.show_navigation(back=True, next=True, cancel=True)

    def page_service_settings(self):
        self.clear_frame()
        ttk.Label(self.frame, text="Installation settings", style="CardTitle.TLabel").pack(anchor="w")

        # Install path
        path_frame = ttk.Frame(self.frame, style="Card.TFrame")
        path_frame.pack(anchor="w", pady=(10, 10), fill="x")

        ttk.Label(path_frame, text="Install path:", style="CardText.TLabel").grid(row=0, column=0, sticky="w")
        path_entry = ttk.Entry(path_frame, textvariable=self.custom_install_path, width=50)
        path_entry.grid(row=0, column=1, padx=8, pady=2, sticky="w")

        def choose_path():
            from tkinter import filedialog
            folder = filedialog.askdirectory()
            if folder:
                self.custom_install_path.set(folder)
                # FIX: Update log file path when user selects install directory
                self.log_file = os.path.join(folder, "install.log")

        ttk.Button(
            path_frame,
            text="Browse…",
            style="Ghost.TButton",
            command=choose_path
        ).grid(row=0, column=2, padx=8, pady=2)

        # Start type
        ttk.Label(
            self.frame,
            text="Service start type:",
            style="CardText.TLabel"
        ).pack(anchor="w", pady=(8, 4))

        ttk.Radiobutton(
            self.frame,
            text="Automatic",
            variable=self.service_start_type,
            value="auto"
        ).pack(anchor="w")
        ttk.Radiobutton(
            self.frame,
            text="Automatic (delayed)",
            variable=self.service_start_type,
            value="delayed"
        ).pack(anchor="w")
        ttk.Radiobutton(
            self.frame,
            text="Manual",
            variable=self.service_start_type,
            value="manual"
        ).pack(anchor="w")
        ttk.Radiobutton(
            self.frame,
            text="Disabled",
            variable=self.service_start_type,
            value="disabled"
        ).pack(anchor="w")

        self.show_navigation(back=True, next=True, cancel=True)

    def page_env_vars(self):
        self.clear_frame()
        ttk.Label(self.frame, text="Environment variables (optional)", style="CardTitle.TLabel").pack(anchor="w")
        ttk.Label(
            self.frame,
            text="You can define additional system-wide environment variables that will be set during installation.",
            style="CardText.TLabel",
            wraplength=640,
            justify="left"
        ).pack(anchor="w", pady=(6, 10))

        var_name = tk.StringVar()
        var_value = tk.StringVar()

        entry_frame = ttk.Frame(self.frame, style="Card.TFrame")
        entry_frame.pack(anchor="w", pady=10)

        ttk.Label(entry_frame, text="Name:").grid(row=0, column=0, sticky="w")
        ttk.Entry(entry_frame, textvariable=var_name, width=30).grid(row=0, column=1, padx=5, pady=2)

        ttk.Label(entry_frame, text="Value:").grid(row=1, column=0, sticky="w")
        ttk.Entry(entry_frame, textvariable=var_value, width=30).grid(row=1, column=1, padx=5, pady=2)

        def add_variable():
            name = var_name.get().strip()
            value = var_value.get().strip()
            if name and value:
                self.env_vars.append((name, value))
                ttk.Label(self.frame, text=f"{name} = {value}", style="CardText.TLabel").pack(anchor="w")
                var_name.set("")
                var_value.set("")

        ttk.Button(self.frame, text="Add variable", style="Ghost.TButton", command=add_variable).pack(anchor="w", pady=(4, 0))

        self.show_navigation(back=True, next=True, cancel=True)

    def page_overview(self):
        self.clear_frame()
        ttk.Label(self.frame, text="Summary", style="CardTitle.TLabel").pack(anchor="w")

        choice = self.user_choice.get()
        install_text = {
            "install": "Install Beszel Agent",
            "uninstall": "Uninstall Beszel Agent",
            "update": "Update existing Beszel Agent"
        }.get(choice, "Unknown")

        ttk.Label(self.frame, text=f"Action: {install_text}", style="CardText.TLabel").pack(anchor="w", pady=(6, 2))
        ttk.Label(self.frame, text=f"Install path: {self.custom_install_path.get()}", style="CardText.TLabel").pack(anchor="w", pady=2)
        ttk.Label(self.frame, text=f"Service start type: {self.service_start_type.get()}", style="CardText.TLabel").pack(anchor="w", pady=2)

        if choice == "install":
            ttk.Label(self.frame, text=f"Public key: {self.user_key.get()}", style="CardText.TLabel").pack(anchor="w", pady=(6, 2))

        if self.env_vars:
            ttk.Label(self.frame, text="Environment variables:", style="CardText.TLabel").pack(anchor="w", pady=(10, 2))
            for name, value in self.env_vars:
                ttk.Label(self.frame, text=f"  {name} = {value}", style="CardText.TLabel").pack(anchor="w")


        self.back_button.pack_forget()
        self.next_button.pack_forget()
        self.cancel_button.pack_forget()

        ttk.Button(
            self.frame,
            text="Confirm and start installation",
            style="Accent.TButton",
            command=self.page_installation
        ).pack(anchor="e", pady=(20, 0))
        self.frame.update_idletasks()
    # ---------- Chocolatey / Download / Install ---------- #

    def check_and_install_choco(self):
        self.log("Checking if Chocolatey is installed...")
        result = subprocess.run("choco -v", shell=True, capture_output=True, text=True)

        if "not recognized" in result.stderr or result.returncode != 0:
            self.log("Chocolatey is not installed. Installing...")
            install_command = (
                "Set-ExecutionPolicy Bypass -Scope Process -Force; "
                "[System.Net.ServicePointManager]::SecurityProtocol = "
                "[System.Net.ServicePointManager]::SecurityProtocol -bor 3072; "
                "iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))"
            )
            result = subprocess.run(["powershell", "-Command", install_command], capture_output=True, text=True)
            self.log(result.stdout + result.stderr)

            if result.returncode != 0:
                self.log("Error: Chocolatey could not be installed!")
                messagebox.showerror("Error", "Chocolatey could not be installed. Please install it manually and try again.")
                return False

            self.log("Waiting 5 seconds for Chocolatey to initialize...")
            time.sleep(5)

            os.environ["PATH"] += os.pathsep + r"C:\ProgramData\chocolatey\bin"
            self.log("Chocolatey added to PATH")

        else:
            self.log("Chocolatey is already installed.")

        return True

    def page_installation(self):
        self.clear_frame()
        ttk.Label(self.frame, text="Installing Beszel Agent…", style="CardTitle.TLabel").pack(anchor="w", pady=(0, 10))

        self.progress = ttk.Progressbar(
            self.frame,
            orient="horizontal",
            length=400,
            mode="determinate",
            style="green.Horizontal.TProgressbar"
        )
        self.progress.pack(pady=10)

        self.install_log_text = scrolledtext.ScrolledText(self.frame, wrap=tk.WORD, height=10, width=80, state=tk.DISABLED)
        self.install_log_text.pack(pady=10, fill="both", expand=True)

        self.show_navigation(back=False, next=False, cancel=False)

        self.progress["value"] = 0

        threading.Thread(target=self.install_agent, daemon=True).start()

    def get_latest_beszel_agent_url(self):
        api_url = "https://api.github.com/repos/henrygd/beszel/releases/latest"
        response = requests.get(api_url)
        if response.status_code == 200:
            data = response.json()
            for asset in data.get("assets", []):
                if "beszel-agent_windows_amd64.zip" in asset.get("name", ""):
                    return asset.get("browser_download_url")
        self.log("Could not determine latest agent version.")
        return None

    def download_file(self, url, dest):
        self.log(f"Downloading {url} to {dest}...")
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            with open(dest, "wb") as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)
            self.log("Download completed.")
        else:
            self.log(f"Download failed: HTTP {response.status_code}")
            messagebox.showerror("Error", f"Error while downloading file: HTTP {response.status_code}")
            return False
        return True

    def extract_zip(self, zip_path, extract_to):
        self.log(f"Checking ZIP file: {zip_path}")

        if not os.path.exists(zip_path) or os.path.getsize(zip_path) == 0:
            self.log("Error: ZIP file missing or empty!")
            messagebox.showerror("Error", "ZIP file missing or empty. Installation aborted.")
            return False

        try:
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                self.log("ZIP is valid. Extracting...")
                zip_contents = zip_ref.namelist()
                self.log(f"ZIP contents: {zip_contents}")

                if not zip_contents:
                    self.log("Error: ZIP is empty after content check!")
                    messagebox.showerror("Error", "ZIP file is empty. Installation aborted.")
                    return False

                os.makedirs(extract_to, exist_ok=True)
                zip_ref.extractall(extract_to)
                self.log("ZIP extraction completed successfully.")

            os.remove(zip_path)
            self.log("ZIP file deleted after extraction.")
            return True

        except zipfile.BadZipFile:
            self.log("Error: ZIP file is corrupted!")
            messagebox.showerror("Error", "The downloaded ZIP file is corrupted. Please try again.")
            return False

        except PermissionError:
            self.log("Error: Permission denied while extracting ZIP!")
            messagebox.showerror("Error", "No permission to extract ZIP. Try running as Administrator.")
            return False

    def install_control_center(self):
        target_dir = os.path.join(self.install_path, "control-center")
        os.makedirs(target_dir, exist_ok=True)

        if not os.path.exists(self.control_center_source):
            self.log("WARNING: Control Center EXE not found in installer directory.")
            return

        target = os.path.join(target_dir, "BeszelAgentControlCenter.exe")
        shutil.copy(self.control_center_source, target)
        self.log(f"Control Center installed at {target}")

    def create_desktop_shortcut(self, target_path):
        """Create a desktop shortcut for the Control Center."""
        try:
            desktop = os.path.join(os.environ["USERPROFILE"], "Desktop")
            shortcut_path = os.path.join(desktop, "Beszel Control Center.lnk")

            # PowerShell Script (absolut stabil)
            ps_script = f'''
                $WshShell = New-Object -ComObject WScript.Shell
                $Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
                $Shortcut.TargetPath = "{target_path}"
                $Shortcut.WorkingDirectory = "{os.path.dirname(target_path)}"
                $Shortcut.IconLocation = "{target_path},0"
                $Shortcut.Save()
                '''

            # Schreibe temporäre PS-Datei
            temp_ps_path = os.path.join(self.install_path, "create_shortcut.ps1")
            with open(temp_ps_path, "w", encoding="utf-8") as f:
                f.write(ps_script)

            # Führe Skript aus
            result = subprocess.run(
                ["powershell", "-ExecutionPolicy", "Bypass", "-File", temp_ps_path],
                capture_output=True, text=True
            )

            # Lösche temporäres Skript
            try:
                os.remove(temp_ps_path)
            except:
                pass

            if result.returncode != 0:
                self.log_install(f"Shortcut creation failed: {result.stderr}")
            else:
                self.log_install(f"Desktop shortcut created at {shortcut_path}")

        except Exception as e:
            self.log_install(f"Error creating shortcut: {e}")

    def copy_installer_self(self):
        """Copy the installer executable (setup.exe) into the install directory."""
        try:
            # Pfad zur exe bestimmen (PyInstaller erzeugt eine .exe im selben Ordner)
            this_installer = os.path.abspath(sys.argv[0])

            if not os.path.exists(this_installer):
                self.log("WARNING: Installer EXE not found — cannot copy setup.exe")
                return

            target_path = os.path.join(self.install_path, "BeszelAgentSetup.exe")
            shutil.copy(this_installer, target_path)

            self.log(f"Installer copied to: {target_path}")
        except Exception as e:
            self.log(f"Failed to copy installer: {e}")

    def install_agent(self):
        self.progress["value"] = 10

        if not self.check_and_install_choco():
            return

        self.log_install("Starting installation...")
        self.install_path = self.custom_install_path.get().strip()
        os.makedirs(self.install_path, exist_ok=True)

        latest_url = self.get_latest_beszel_agent_url()
        if not latest_url:
            self.log("Error: Could not retrieve latest Beszel Agent version.")
            messagebox.showerror("Error", "Could not retrieve latest Beszel Agent version.")
            return

        zip_path = os.path.join(self.downloads_folder, "beszel-agent.zip")

        self.log_install("Downloading latest Beszel Agent...")
        if not self.download_file(latest_url, zip_path):
            return

        extract_path = os.path.join(self.downloads_folder, "beszel-agent-extracted")
        shutil.rmtree(extract_path, ignore_errors=True)
        os.makedirs(extract_path, exist_ok=True)

        self.log_install("Extracting agent ZIP...")
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(extract_path)

        agent_exe_path = None
        for name in os.listdir(extract_path):
            if name.startswith("beszel-agent") and name.endswith(".exe"):
                agent_exe_path = os.path.join(extract_path, name)
                break

        if not agent_exe_path:
            messagebox.showerror("Error", "Extracted Beszel Agent EXE not found.")
            return

        final_agent_path = os.path.join(self.install_path, "beszel-agent.exe")
        shutil.copy(agent_exe_path, final_agent_path)
        self.log_install(f"Agent copied to: {final_agent_path}")

        # ---------------------------------------
        # NEW: Extract and save installed version
        # ---------------------------------------
        import re
        version_match = re.search(r"v?(\d+\.\d+\.\d+)", latest_url)
        installed_version = version_match.group(1) if version_match else "Unknown"

        self.log_install(f"Detected Beszel Agent version: {installed_version}")
        self.log_install("Writing installed version to registry...")

        subprocess.run(
            [
                "reg", "add",
                r"HKLM\SYSTEM\CurrentControlSet\Services\beszelagent\Parameters",
                "/v", "InstalledVersion",
                "/t", "REG_SZ",
                "/d", installed_version,
                "/f"
            ],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            creationflags=0x08000000
        )

        self.log_install("Installing Control Center...")
        self.install_control_center()

        # Create desktop shortcut
        control_center_exe = os.path.join(self.install_path, "control-center", "BeszelAgentControlCenter.exe")
        if os.path.exists(control_center_exe):
            self.log_install("Creating desktop shortcut...")
            self.create_desktop_shortcut(control_center_exe)
        else:
            self.log_install("Control Center executable not found — cannot create shortcut.")

        self.log_install("Copying installer to install directory...")
        self.copy_installer_self()


        self.log_install("Installing NSSM...")
        result = subprocess.run(
            "choco install nssm -y",
            shell=True,
            capture_output=True,
            text=True
        )
        self.log(result.stdout + result.stderr)

        nssm_path = r"C:\ProgramData\chocolatey\bin\nssm.exe"
        if not os.path.exists(nssm_path):
            messagebox.showerror("Error", "NSSM not found after installation.")
            return

        self.progress["value"] = 30

        self.log_install("Creating service via NSSM...")
        subprocess.run(
            [nssm_path, "install", "beszelagent", final_agent_path],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            creationflags=0x08000000
        )

        start_type_map = {
            "auto": "SERVICE_AUTO_START",
            "delayed": "SERVICE_DELAYED_START",
            "manual": "SERVICE_DEMAND_START",
            "disabled": "SERVICE_DISABLED"
        }

        st = self.service_start_type.get()
        if st in start_type_map:
            subprocess.run(
                [nssm_path, "set", "beszelagent", "Start", start_type_map[st]],
                stdin=subprocess.DEVNULL,
                creationflags=0x08000000
            )

        if self.user_key.get():
            subprocess.run(
                [nssm_path, "set", "beszelagent", "AppEnvironmentExtra", f"KEY={self.user_key.get()}"],
                stdin=subprocess.DEVNULL,
                creationflags=0x08000000
            )
            self.log_install("Public KEY applied.")

        if self.env_vars:
            self.log_install("Applying environment variables...")
            for name, value in self.env_vars:
                subprocess.run(
                    [
                        "reg", "add",
                        r"HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment",
                        "/v", name, "/t", "REG_SZ", "/d", value, "/f"
                    ],
                    stdin=subprocess.DEVNULL,
                    capture_output=True,
                    text=True,
                    creationflags=0x08000000
                )

        self.progress["value"] = 50

        self.log_install("Starting service...")
        subprocess.run(
            ["sc", "start", "beszelagent"],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            creationflags=0x08000000
        )

        time.sleep(2)

        status = subprocess.run(
            ["sc", "query", "beszelagent"],
            capture_output=True,
            text=True,
            creationflags=0x08000000
        ).stdout

        if "RUNNING" not in status.upper():
            messagebox.showerror("Service Error", "Beszel Agent failed to start. Check logs.")
            self.log("SERVICE FAILED TO START")
        else:
            self.log("Service is running.")

        rule_name = "Beszel Agent"
        check = subprocess.run(
            ["powershell", "-Command", f"Get-NetFirewallRule -DisplayName '{rule_name}' | Out-String"],
            capture_output=True,
            text=True,
            creationflags=0x08000000
        )

        if rule_name not in check.stdout:
            self.log("Creating firewall rule...")
            subprocess.run(
                [
                    "powershell",
                    "-Command",
                    "New-NetFirewallRule -DisplayName 'Beszel Agent' -Direction Inbound -LocalPort 45876 -Protocol TCP -Action Allow"
                ],
                capture_output=True,
                text=True,
                creationflags=0x08000000
            )

        self.progress["value"] = 100
        self.root.after(2000, self.page_summary)

    # ---------- Uninstall ---------- #

    def page_uninstall(self):
        self.clear_frame()
        ttk.Label(self.frame, text="Uninstall Beszel Agent", style="CardTitle.TLabel").pack(anchor="w", pady=(0, 10))

        self.progress = ttk.Progressbar(
            self.frame,
            orient="horizontal",
            length=400,
            mode="determinate",
            style="green.Horizontal.TProgressbar"
        )
        self.progress.pack(pady=10)

        self.uninstall_log_text = scrolledtext.ScrolledText(self.frame, wrap=tk.WORD, height=10, width=80, state=tk.DISABLED)
        self.uninstall_log_text.pack(pady=10, fill="both", expand=True)

        self.show_navigation(back=False, next=False, cancel=False)

        self.progress["value"] = 0

        self.root.after(200, self.uninstall_agent)

    def uninstall_agent(self):
        self.log_uninstall("Starting uninstallation...")
        self.progress["value"] = 20

        nssm_path = r"C:\ProgramData\chocolatey\bin\nssm.exe"
        service_name = "beszelagent"

        # Stop service
        self.log_uninstall("Stopping service...")
        stop_result = subprocess.run(
            [nssm_path, "stop", service_name],
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
            creationflags=0x08000000
        )
        self.log_uninstall(stop_result.stdout + stop_result.stderr)

        self.progress["value"] = 40

# -------- NEW: Delete install directory via Registry -------- #

        # Registry key identical to control center logic
        reg_key = r"HKLM\SYSTEM\CurrentControlSet\Services\beszelagent\Parameters"

        try:
            result = subprocess.run(
                ["reg", "query", reg_key, "/v", "Application"],
                capture_output=True,
                text=True,
                creationflags=0x08000000
            )
            out = result.stdout

            if "Application" in out:
                # Determine REG type
                if "REG_EXPAND_SZ" in out:
                    parts = out.split("REG_EXPAND_SZ")
                elif "REG_SZ" in out:
                    parts = out.split("REG_SZ")
                else:
                    parts = None

                if parts:
                    raw_path = parts[1].strip().strip('"')
                    expanded = os.path.expandvars(raw_path)
                    # Remove EXE name → keep folder
                    install_dir = os.path.dirname(expanded)
                else:
                    install_dir = None
            else:
                install_dir = None

        except Exception as e:
            install_dir = None

        if not install_dir or not os.path.exists(install_dir):
            self.log_uninstall(f"Install directory not found via registry. Value: {install_dir}")
        else:
            self.log_uninstall(f"Removing installation directory: {install_dir}")

            try:
                if os.path.exists(install_dir):
                    shutil.rmtree(install_dir, ignore_errors=True)

                # Double check (Windows sometimes locks files)
                if os.path.exists(install_dir):
                    self.log_uninstall("Warning: Directory still exists, retrying...")
                    time.sleep(1)
                    shutil.rmtree(install_dir, ignore_errors=True)

                if not os.path.exists(install_dir):
                    self.log_uninstall("Directory removed successfully.")
                else:
                    self.log_uninstall("Warning: Could not fully delete directory.")

            except Exception as e:
                self.log_uninstall(f"Error deleting directory: {e}")

        self.progress["value"] = 90
        self.log_uninstall("Uninstallation completed.")
        self.installation_status = "Uninstallation successful!"
        self.progress["value"] = 100
        self.root.after(2000, self.page_summary)

        # Remove service
        self.log_uninstall("Removing service...")
        remove_result = subprocess.run(
            [nssm_path, "remove", service_name, "confirm"],
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
            creationflags=0x08000000
        )
        self.log_uninstall(remove_result.stdout + remove_result.stderr)

        self.progress["value"] = 60

    # ---------- Update ---------- #

    def page_update(self):
        self.clear_frame()
        ttk.Label(self.frame, text="Updating Beszel Agent…", style="CardTitle.TLabel").pack(anchor="w", pady=(0, 10))

        self.progress = ttk.Progressbar(
            self.frame,
            orient="horizontal",
            length=400,
            mode="determinate",
            style="green.Horizontal.TProgressbar"
        )
        self.progress.pack(pady=10)

        self.log_text = scrolledtext.ScrolledText(self.frame, wrap=tk.WORD, height=10, width=80, state=tk.DISABLED)
        self.log_text.pack(pady=10, fill="both", expand=True)

        self.show_navigation(back=False, next=False, cancel=False)

        self.progress["value"] = 0

        self.root.after(500, self.update_agent)

    def update_agent(self):
        self.log_to_gui("Starting Beszel Agent update...")
        self.progress["value"] = 10

        agent_path = os.path.join(self.install_path, "beszel-agent.exe")

        if not os.path.exists(agent_path):
            self.log_to_gui("Error: Beszel Agent not found! Update aborted.")
            messagebox.showerror("Update error", "Beszel Agent not found. Cannot update.")
            self.root.after(1000, self.page_summary)
            return

        update_command = f'powershell -Command "& {{Set-Location -Path \'{self.install_path}\'; ./beszel-agent update }}"'

        self.progress["value"] = 40

        try:
            result = subprocess.run(update_command, shell=True, capture_output=True, text=True)
            self.log_to_gui(result.stdout + result.stderr)

            if result.returncode == 0:
                self.log_to_gui("Update completed successfully.")
            else:
                self.log_to_gui(f"Update failed with code: {result.returncode}")
                messagebox.showerror("Update error", f"Beszel Agent update failed. Code: {result.returncode}")
        except Exception as e:
            self.log_to_gui(f"Update error: {e}")
            messagebox.showerror("Update error", f"Error during update: {e}")

        self.progress["value"] = 100

        ttk.Button(self.frame, text="Close", style="Accent.TButton", command=self.root.quit).pack(anchor="e", pady=10)

    # ---------- Summary ---------- #

    def page_summary(self):
        self.clear_frame()
        ttk.Label(self.frame, text="Setup finished", style="CardTitle.TLabel").pack(anchor="w", pady=(0, 10))
        ttk.Label(
            self.frame,
            text="The operation has completed. You can now close this installer.",
            style="CardText.TLabel",
            wraplength=640,
            justify="left"
        ).pack(anchor="w", pady=(4, 10))

        self.show_navigation(back=False, next=False, cancel=False)

        ttk.Button(self.frame, text="Exit", style="Accent.TButton", command=self.root.quit).pack(anchor="e", pady=10)

    # ---------- Logging helpers ---------- #

    def log_to_gui(self, message):
        self.log(message)
        if self.log_text is not None:
            self.log_text.config(state=tk.NORMAL)
            self.log_text.insert(tk.END, message + "\n")
            self.log_text.config(state=tk.DISABLED)
            self.log_text.yview(tk.END)

    def log_uninstall(self, message):
        self.log(message)
        if self.uninstall_log_text is not None:
            self.uninstall_log_text.config(state=tk.NORMAL)
            self.uninstall_log_text.insert(tk.END, message + "\n")
            self.uninstall_log_text.config(state=tk.DISABLED)
            self.uninstall_log_text.yview(tk.END)
        self.root.update_idletasks()

    def log_install(self, message):
        self.log(message)

        def write():
            if self.install_log_text is not None:
                self.install_log_text.config(state=tk.NORMAL)
                self.install_log_text.insert(tk.END, message + "\n")
                self.install_log_text.config(state=tk.DISABLED)
                self.install_log_text.yview(tk.END)

        self.root.after(0, write)


if __name__ == "__main__":
    root = tk.Tk()
    # Titlebar Icon
    try:
        root.iconbitmap(icon_path)
    except:
        print("Could not load icon", icon_path)
    # Taskbar Icon Fix (Windows)
    myappid = u"Beszel.Agent.Installer"  # unique ID
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    style = ttk.Style()
    app = InstallerApp(root)
    apply_theme(root)
    root.update_idletasks()
    root.geometry(f"{root.winfo_reqwidth()}x{root.winfo_reqheight()}")
    root.mainloop()
