import tkinter as tk
from tkinter import filedialog, messagebox
import qrcode
import pandas as pd
from PIL import Image, ImageTk
import fitz  # PyMuPDF
import io

class flyerQRAutomation:
    def __init__(self, root):
        self.root = root
        self.root.title("QR Code PDF Generator")

        self.canvas = tk.Canvas(root, width=600, height=400, bg="gray")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.load_pdf_button = tk.Button(root, text="Load PDF Template", command=self.load_file)
        self.load_pdf_button.pack(pady=5)

        self.load_csv_button = tk.Button(root, text="Load CSV File", command=self.load_csv)
        self.load_csv_button.pack(pady=5)

        self.generate_button = tk.Button(root, text="Generate QR PDF", command=self.process_qr)
        self.generate_button.pack(pady=5)

        self.canvas.bind("<ButtonPress-1>", self.start_selection)
        self.canvas.bind("<B1-Motion>", self.draw_selection)
        self.canvas.bind("<ButtonRelease-1>", self.finish_selection)

        self.pdf_path = None
        self.qr_position = None
        self.data = None
        self.pdf_width = 0
        self.pdf_height = 0
        self.scale_x = 1
        self.scale_y = 1

    def load_file(self):
        """Load a PDF template and display the first page as an image preview."""
        file_path = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if file_path:
            self.pdf_path = file_path
            doc = fitz.open(self.pdf_path)
            pix = doc[0].get_pixmap()
            self.pdf_width, self.pdf_height = pix.width, pix.height  # Store full-size PDF dimensions
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            # Resize for preview while maintaining aspect ratio
            preview_width, preview_height = 600, int(600 * (pix.height / pix.width))
            img.thumbnail((preview_width, preview_height))
            self.scale_x = self.pdf_width / preview_width
            self.scale_y = self.pdf_height / preview_height

            self.tk_img = ImageTk.PhotoImage(img)
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_img)

            messagebox.showinfo("Success", f"Loaded PDF: {self.pdf_path}")

    def load_csv(self):
        """Load a CSV file containing 'Link', 'Name', and 'Amount'."""
        file_path = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
        if file_path:
            try:
                self.data = pd.read_csv(file_path, encoding="utf-8-sig")
                self.data.columns = self.data.columns.str.strip()  # Remove extra spaces

                # Ensure required columns exist
                if not all(col in self.data.columns for col in ["Link", "Name", "Amount"]):
                    raise ValueError("CSV must contain 'Link', 'Name', and 'Amount' columns.")

                messagebox.showinfo("Success", f"Loaded CSV: {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load CSV: {e}")

    def start_selection(self, event):
        """Start selecting the QR placement area."""
        self.start_x, self.start_y = event.x, event.y
        self.rect_id = self.canvas.create_rectangle(self.start_x, self.start_y, event.x, event.y, outline="red")

    def draw_selection(self, event):
        """Draw selection rectangle for QR placement."""
        self.canvas.coords(self.rect_id, self.start_x, self.start_y, event.x, event.y)

    def finish_selection(self, event):
        """Save QR placement coordinates and scale them to full PDF size."""
        x1, y1, x2, y2 = self.start_x, self.start_y, event.x, event.y
        self.qr_position = (
            int(x1 * self.scale_x),
            int(y1 * self.scale_y),
            int(x2 * self.scale_x),
            int(y2 * self.scale_y),
        )
        print(f"QR Position Selected (PDF Coordinates): {self.qr_position}")

    def generate_qr_code(self, data, qr_size=200):
        """Generate a QR code without a white border."""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=1  # Removes extra white padding
        )
        qr.add_data(data)
        qr.make(fit=True)
        return qr.make_image(fill="black", back_color="white")

    def overlay_qr_on_pdf(self, output_path):
        """Generate a single PDF containing all QR codes and names with correct amounts."""
        if not self.pdf_path:
            messagebox.showerror("Error", "Please load a PDF template first.")
            return

        if self.data is None:
            messagebox.showerror("Error", "Please load a CSV file first.")
            return

        if not self.qr_position:
            messagebox.showerror("Error", "Please select a position for the QR code.")
            return

        doc = fitz.open(self.pdf_path)
        new_doc = fitz.open()  # New document for output
        x1, y1, x2, y2 = self.qr_position
        qr_size = (x2 - x1, y2 - y1)

        for _, row in self.data.iterrows():
            link = row['Link']
            name = row['Name']
            amount = int(row['Amount'])

            qr_img = self.generate_qr_code(link).resize(qr_size)

            # Convert QR code to in-memory PNG
            img_buffer = io.BytesIO()
            qr_img.save(img_buffer, format="PNG")
            img_buffer.seek(0)

            for _ in range(amount):  # Duplicate pages based on "Amount"
                template_page = doc[0]  # Always use the first page as a template
                new_page = new_doc.new_page(width=template_page.rect.width, height=template_page.rect.height)
                new_page.show_pdf_page(new_page.rect, doc, 0)  # Copy original template page

                # Insert QR code
                rect = fitz.Rect(x1, y1, x2, y2)
                new_page.insert_image(rect, stream=img_buffer.getvalue())

                # Add name in bottom right corner
                text_position = (new_page.rect.width - 100, new_page.rect.height - 30)
                new_page.insert_text(text_position, name, fontsize=10, color=(0, 0, 0))

        new_doc.save(output_path)
        messagebox.showinfo("Success", f"QR PDF Generated: {output_path}")

    def process_qr(self):
        """Generate QR codes and apply them to PDFs."""
        output_file = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF Files", "*.pdf")])
        if output_file:
            self.overlay_qr_on_pdf(output_file)


if __name__ == "__main__":
    root = tk.Tk()
    app = flyerQRAutomation(root)
    root.mainloop()
