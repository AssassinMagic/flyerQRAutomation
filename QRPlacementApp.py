import tkinter as tk
from tkinter import filedialog, messagebox
import qrcode
from PIL import Image, ImageTk
import fitz  # PyMuPDF
import io

class QRPlacementApp:
    def __init__(self, root):
        self.root = root
        self.root.title("QR Code Placement Tool")

        self.canvas = tk.Canvas(root, width=600, height=400, bg="gray")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.load_button = tk.Button(root, text="Load Image/PDF", command=self.load_file)
        self.load_button.pack(pady=5)

        self.link_entry = tk.Text(root, height=5, width=50)
        self.link_entry.pack(pady=5)
        self.link_entry.insert(tk.END, "Enter up to 100 links (one per line)")

        self.generate_button = tk.Button(root, text="Generate QR Codes", command=self.process_qr)
        self.generate_button.pack(pady=5)

        self.canvas.bind("<ButtonPress-1>", self.start_selection)
        self.canvas.bind("<B1-Motion>", self.draw_selection)
        self.canvas.bind("<ButtonRelease-1>", self.finish_selection)

        self.image_path = None
        self.pdf_path = None
        self.image = None
        self.qr_position = None
        self.scale_x = 1
        self.scale_y = 1

    def load_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Images", "*.png;*.jpg;*.jpeg"), ("PDF Files", "*.pdf")])
        if file_path.endswith(".pdf"):
            self.pdf_path = file_path
            self.image_path = None
            doc = fitz.open(self.pdf_path)
            pix = doc[0].get_pixmap()
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            self.image = img
        else:
            self.image_path = file_path
            self.pdf_path = None
            self.image = Image.open(self.image_path)

        self.display_image()

    def display_image(self):
        """Scales the image to fit the Tkinter canvas while preserving aspect ratio."""
        self.img_width, self.img_height = self.image.size  # Actual image size

        # Scale image to fit within the canvas
        canvas_width = 600
        canvas_height = 400
        self.image.thumbnail((canvas_width, canvas_height))  # Resize for display
        self.tk_img = ImageTk.PhotoImage(self.image)

        # Calculate scale factors
        self.scale_x = self.img_width / self.image.width
        self.scale_y = self.img_height / self.image.height

        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_img)

    def start_selection(self, event):
        """Start selecting a region for QR placement."""
        self.start_x, self.start_y = event.x, event.y
        self.rect_id = self.canvas.create_rectangle(self.start_x, self.start_y, event.x, event.y, outline="red")

    def draw_selection(self, event):
        """Draw a rectangle as the user selects a region."""
        self.canvas.coords(self.rect_id, self.start_x, self.start_y, event.x, event.y)

    def finish_selection(self, event):
        """Save the QR placement coordinates (scaled to actual image size)."""
        x1, y1, x2, y2 = self.start_x, self.start_y, event.x, event.y
        self.qr_position = (
            int(x1 * self.scale_x),
            int(y1 * self.scale_y),
            int(x2 * self.scale_x),
            int(y2 * self.scale_y)
        )
        print(f"Scaled QR Position: {self.qr_position}")

    def generate_qr_code(self, data, qr_size=200):
        """Generate a QR code without a white border."""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=0  # Removes the white border
        )
        qr.add_data(data)
        qr.make(fit=True)
        qr_img = qr.make_image(fill="black", back_color="white")
        return qr_img

    def overlay_qr_on_image(self, qr_img, output_path):
        """Overlay a QR code onto the actual image at the correct position."""
        x1, y1, x2, y2 = self.qr_position
        qr_img = qr_img.resize((x2 - x1, y2 - y1))

        # Convert QR to an opaque image (removes transparency issue)
        qr_img = qr_img.convert("RGB")

        # Open the base image in RGB mode
        base_img = Image.open(self.image_path).convert("RGB")
    
        # Paste QR code without transparency
        base_img.paste(qr_img, (x1, y1))

        base_img.save(output_path, "PNG")

    def overlay_qr_on_pdf(self, qr_img, output_path):
        """Overlay a QR code onto the actual PDF at the correct position."""
        doc = fitz.open(self.pdf_path)
        for page in doc:
            x1, y1, x2, y2 = self.qr_position

            # Convert QR code to an in-memory PNG (Fixes encoder issue)
            img_buffer = io.BytesIO()
            qr_img.save(img_buffer, format="PNG")  # Save as PNG in memory
            img_buffer.seek(0)  # Move to start of buffer
        
            # Insert the in-memory PNG into the PDF
            rect = fitz.Rect(x1, y1, x2, y2)
            page.insert_image(rect, stream=img_buffer.getvalue())

        doc.save(output_path)

    def process_qr(self):
        """Generate and overlay QR codes for each entered link."""
        if not self.qr_position:
            messagebox.showerror("Error", "Please select a position for the QR code.")
            return

        links = self.link_entry.get("1.0", tk.END).strip().split("\n")
        links = [link.strip() for link in links if link.strip()]
        if len(links) > 20:
            messagebox.showerror("Error", "You can enter up to 20 links only.")
            return

        for i, link in enumerate(links):
            qr_img = self.generate_qr_code(link)

            if self.image_path:
                output_file = f"output_image_{i+1}.png"
                self.overlay_qr_on_image(qr_img, output_file)
            elif self.pdf_path:
                output_file = f"output_pdf_{i+1}.pdf"
                self.overlay_qr_on_pdf(qr_img, output_file)

            print(f"Generated: {output_file}")

        messagebox.showinfo("Success", "QR codes have been generated and saved!")

if __name__ == "__main__":
    root = tk.Tk()
    root.lift()  
    root.attributes('-topmost', True)  # Ensures window pops up
    app = QRPlacementApp(root)
    root.mainloop()
