import os
import sys
import fitz  # PyMuPDF
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel, QLineEdit, QPushButton, QFileDialog,
    QMessageBox, QVBoxLayout, QWidget, QHBoxLayout, QCheckBox, QDialog,QInputDialog
)
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtCore import Qt
import hashlib


# Secure credentials (hashed password for "admin")
SECURE_USERNAME = "admin"
SECURE_PASSWORD_HASH = hashlib.sha256("12345678".encode()).hexdigest()  # Replace with your hashed password

def authenticate_user():
    """
    Authenticates the user by prompting for a username and password.
    Returns True if authentication is successful, False otherwise.
    """
    username, ok = QInputDialog.getText(None, "Login", "Enter Username:", QLineEdit.Normal)
    if not ok or not username:
        return False

    password, ok = QInputDialog.getText(None, "Login", "Enter Password:", QLineEdit.Password)
    if not ok or not password:
        return False

    # Hash the entered password
    entered_password_hash = hashlib.sha256(password.encode()).hexdigest()

    # Check credentials
    if username == SECURE_USERNAME and entered_password_hash == SECURE_PASSWORD_HASH:
        return True
    else:
        QMessageBox.critical(None, "Authentication Failed", "Invalid username or password.")
        return False

def decrypt_pdf(pdf_path, password):
    """
    Decrypts a password-protected PDF using PyMuPDF.
    Returns the decrypted document if successful, otherwise None.
    """
    doc = fitz.open(pdf_path)
    
    # Check if the PDF is encrypted
    if doc.is_encrypted:
        try:
            if not doc.authenticate(password):
                raise ValueError("Incorrect password. Unable to decrypt the PDF.")
        except Exception as e:
            return None
    
    return doc
def validate_and_set_cropbox(page, left, top, right, bottom):
    """
    Validates and sets the crop box for a PDF page.
    Ensures the crop box is within the page's MediaBox.
    """
    mediabox = page.mediabox

    # Ensure the crop box is within the MediaBox
    left = max(left, mediabox.x0)
    top = max(top, mediabox.y0)
    right = min(right, mediabox.x1)
    bottom = min(bottom, mediabox.y1)

    # Create the crop box
    cropbox = fitz.Rect(left, top, right, bottom)

    # Check if the crop box is valid (non-zero area)
    if cropbox.is_empty or cropbox.width <= 0 or cropbox.height <= 0:
        raise ValueError("Invalid crop box: The crop box has zero or negative area.")

    # Set the crop box
    page.set_cropbox(cropbox)
def crop_pdf_page(doc, page_num, left, top, right, bottom):
    """
    Crops a specific region of a PDF page.
    Returns the cropped page as a new PDF document.
    """
    cropped_doc = fitz.open()
    page = doc.load_page(page_num)
    validate_and_set_cropbox(page, left, top, right, bottom)
    cropped_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
    return cropped_doc

def pdf_to_image(pdf_path, output_image_path, dpi=300):
    """
    Converts the first page of a PDF to an image.
    """
    doc = fitz.open(pdf_path)
    page = doc.load_page(0)
    pix = page.get_pixmap(dpi=dpi)
    pix.save(output_image_path)

class PreviewDialog(QDialog):
    def __init__(self, image_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cropped Image Preview")
        self.setGeometry(200, 200, 800, 600)

        layout = QVBoxLayout()

        # Load and display the image
        pixmap = QPixmap(image_path)
        label = QLabel(self)
        label.setPixmap(pixmap)
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        # Add a confirmation button
        confirm_button = QPushButton("Confirm")
        confirm_button.setStyleSheet("background-color: #4CAF50; color: white; padding: 5px 10px;")
        confirm_button.clicked.connect(self.accept)  # Close the dialog when confirmed
        layout.addWidget(confirm_button)

        self.setLayout(layout)

class AadhaarCropperApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Aadhaar PDF Cropper")
        self.setGeometry(100, 100, 800, 600)  # Set window size

        # Initialize variables
        self.file_path = ""
        self.pdf_password = ""
        self.left = 0
        self.top = 400
        self.right = 612
        self.bottom = 792
        self.cropped_image_path = "cropped_aadhaar.png"

        # Set up the UI
        self.init_ui()

    def init_ui(self):
        # Main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Title Label
        title_label = QLabel("Aadhaar PDF Cropper")
        title_label.setFont(QFont("Arial", 18, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #333; margin-bottom: 20px;")
        layout.addWidget(title_label)

        # File Selection
        file_layout = QHBoxLayout()
        file_label = QLabel("Select PDF File:")
        file_label.setFont(QFont("Arial", 12))
        self.file_entry = QLineEdit()
        self.file_entry.setPlaceholderText("No file selected")
        self.file_entry.setStyleSheet("padding: 5px; border: 1px solid #ccc;")
        browse_button = QPushButton("Browse")
        browse_button.setStyleSheet("background-color: #4CAF50; color: white; padding: 5px 10px;")
        browse_button.clicked.connect(self.browse_file)
        file_layout.addWidget(file_label)
        file_layout.addWidget(self.file_entry)
        file_layout.addWidget(browse_button)
        layout.addLayout(file_layout)

        # Password Input
        password_layout = QHBoxLayout()
        self.password_checkbox = QCheckBox("Password Protected?")
        self.password_checkbox.setFont(QFont("Arial", 12))
        self.password_entry = QLineEdit()
        self.password_entry.setEchoMode(QLineEdit.Password)
        self.password_entry.setEnabled(False)
        self.password_entry.setStyleSheet("padding: 5px; border: 1px solid #ccc;")
        self.password_checkbox.stateChanged.connect(self.toggle_password_input)
        password_layout.addWidget(self.password_checkbox)
        password_layout.addWidget(self.password_entry)
        layout.addLayout(password_layout)

        # Crop Coordinates
        coord_layout = QVBoxLayout()
        coord_label = QLabel("Crop Coordinates:")
        coord_label.setFont(QFont("Arial", 14, QFont.Bold))
        coord_label.setStyleSheet("margin-top: 20px; margin-bottom: 10px;")
        coord_layout.addWidget(coord_label)

        # Left
        left_layout = QHBoxLayout()
        left_label = QLabel("Left:")
        left_label.setFont(QFont("Arial", 12))
        self.left_entry = QLineEdit(str(self.left))
        self.left_entry.setStyleSheet("padding: 5px; border: 1px solid #ccc;")
        left_layout.addWidget(left_label)
        left_layout.addWidget(self.left_entry)
        coord_layout.addLayout(left_layout)

        # Top
        top_layout = QHBoxLayout()
        top_label = QLabel("Top:")
        top_label.setFont(QFont("Arial", 12))
        self.top_entry = QLineEdit(str(self.top))
        self.top_entry.setStyleSheet("padding: 5px; border: 1px solid #ccc;")
        top_layout.addWidget(top_label)
        top_layout.addWidget(self.top_entry)
        coord_layout.addLayout(top_layout)

        # Right
        right_layout = QHBoxLayout()
        right_label = QLabel("Right:")
        right_label.setFont(QFont("Arial", 12))
        self.right_entry = QLineEdit(str(self.right))
        self.right_entry.setStyleSheet("padding: 5px; border: 1px solid #ccc;")
        right_layout.addWidget(right_label)
        right_layout.addWidget(self.right_entry)
        coord_layout.addLayout(right_layout)

        # Bottom
        bottom_layout = QHBoxLayout()
        bottom_label = QLabel("Bottom:")
        bottom_label.setFont(QFont("Arial", 12))
        self.bottom_entry = QLineEdit(str(self.bottom))
        self.bottom_entry.setStyleSheet("padding: 5px; border: 1px solid #ccc;")
        bottom_layout.addWidget(bottom_label)
        bottom_layout.addWidget(self.bottom_entry)
        coord_layout.addLayout(bottom_layout)

        layout.addLayout(coord_layout)

        # Process Button
        process_button = QPushButton("Process PDF")
        process_button.setStyleSheet("background-color: #4CAF50; color: white; font-size: 16px; padding: 10px;")
        process_button.clicked.connect(self.process_pdf)
        layout.addWidget(process_button)

        # Print Button (Initially Disabled)
        self.print_button = QPushButton("Print")
        self.print_button.setStyleSheet("background-color: #f44336; color: white; font-size: 16px; padding: 10px;")
        self.print_button.setEnabled(False)  # Disabled until preview is confirmed
        self.print_button.clicked.connect(self.print_image)
        layout.addWidget(self.print_button)

        # Exit Button
        exit_button = QPushButton("Exit")
        exit_button.setStyleSheet("background-color: #f44336; color: white; font-size: 16px; padding: 10px;")
        exit_button.clicked.connect(self.close)
        layout.addWidget(exit_button)

    def browse_file(self):
        """Opens a file dialog to select a PDF file."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Select PDF File", "", "PDF Files (*.pdf)")
        if file_path:
            self.file_path = file_path
            self.file_entry.setText(file_path)

    def toggle_password_input(self, state):
        """Enables/disables the password input field based on the checkbox."""
        self.password_entry.setEnabled(state == Qt.Checked)

    def process_pdf(self):
        """Processes the PDF based on user inputs."""
        if not self.file_path:
            QMessageBox.warning(self, "Error", "Please select a PDF file.")
            return

        # Get crop coordinates
        try:
            self.left = int(self.left_entry.text())
            self.top = int(self.top_entry.text())
            self.right = int(self.right_entry.text())
            self.bottom = int(self.bottom_entry.text())
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Please enter valid integers for crop coordinates.")
            return

        # Get password if applicable
        if self.password_checkbox.isChecked():
            self.pdf_password = self.password_entry.text()
        else:
            self.pdf_password = None

        # Step 1: Decrypt the PDF if it's password-protected
        doc = decrypt_pdf(self.file_path, self.pdf_password)
        if doc is None:
            QMessageBox.critical(self, "Error", "Failed to decrypt the PDF. Please check the password.")
            return

        # Step 2: Crop the PDF page
        try:
            cropped_doc = crop_pdf_page(doc, page_num=0, left=self.left, top=self.top, right=self.right, bottom=self.bottom)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to crop the PDF: {e}")
            return

        # Save the cropped PDF
        cropped_pdf_path = "cropped_aadhaar.pdf"
        cropped_doc.save(cropped_pdf_path)

        # Step 3: Convert the cropped PDF page to an image
        pdf_to_image(cropped_pdf_path, self.cropped_image_path)

        # Step 4: Preview the cropped image
        self.preview_image()

    def preview_image(self):
        """Previews the cropped image in a separate window."""
        if not os.path.exists(self.cropped_image_path):
            QMessageBox.warning(self, "Error", "No cropped image found. Please process the PDF first.")
            return

        dialog = PreviewDialog(self.cropped_image_path, self)
        if dialog.exec_() == QDialog.Accepted:
            # Enable the print button after preview confirmation
            self.print_button.setEnabled(True)
            QMessageBox.information(self, "Success", "Preview confirmed. You can now print the cropped image.")

    def print_image(self):
        """Sends the cropped image to the printer."""
        if not os.path.exists(self.cropped_image_path):
            QMessageBox.warning(self, "Error", "No cropped image found. Please process the PDF first.")
            return

        try:
            import win32api
            win32api.ShellExecute(0, "print", self.cropped_image_path, None, ".", 0)
            QMessageBox.information(self, "Printing", "File sent to the default printer.")
        except Exception as e:
            QMessageBox.critical(self, "Printing Error", f"Failed to print: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # Use Fusion style for a modern look

    # Authenticate the user
    if not authenticate_user():
        sys.exit()

    # Run the application
    window = AadhaarCropperApp()
    window.show()
    sys.exit(app.exec_())