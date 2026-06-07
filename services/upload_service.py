import os
import time
from werkzeug.utils import secure_filename


def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions


def save_uploaded_image(file, upload_folder, allowed_extensions):
    if not file or not file.filename or not allowed_file(file.filename, allowed_extensions):
        return None

    filename = secure_filename(file.filename)
    filename = f"{int(time.time())}_{filename}"
    os.makedirs(upload_folder, exist_ok=True)
    file_path = os.path.join(upload_folder, filename)
    file.save(file_path)
    return filename
