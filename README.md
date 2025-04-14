# Story Scene Generator

Ứng dụng chuyển đổi câu chuyện thành các cảnh và tạo hình ảnh minh họa, âm thanh, và video tự động.

## Tính năng

- Chuyển đổi văn bản câu chuyện thành các cảnh riêng biệt
- Tạo mô tả hình ảnh cho mỗi cảnh
- Tạo hình ảnh minh họa từ mô tả bằng AI
- Tạo file âm thanh từ nội dung cảnh bằng text-to-speech
- Tạo video từ ảnh và âm thanh các cảnh
- Quản lý nhiều câu chuyện với hệ thống ID
- Lưu trữ dữ liệu vào bộ nhớ cache để tránh tạo lại nội dung không cần thiết

## Yêu cầu

- Python 3.6+
- Các thư viện: openai, requests, google-cloud-texttospeech, moviepy
- API key của NVIDIA để sử dụng dịch vụ tạo hình ảnh và LLM
- File chứng thực Google Cloud cho dịch vụ Text-to-Speech

## Cài đặt

1. Clone repository
```bash
git clone https://github.com/username/storyTeller.git
cd storyTeller
```

2. Tạo và kích hoạt môi trường ảo
```bash
# Tạo môi trường ảo
python -m venv .venv

# Kích hoạt môi trường ảo (Windows)
.venv\Scripts\activate

# Kích hoạt môi trường ảo (Linux/Mac)
source .venv/bin/activate
```

3. Cài đặt các phụ thuộc
```bash
# Cài đặt tất cả các thư viện từ requirements.txt
pip install -r requirements.txt
```

4. Thiết lập API key

**Tùy chọn 1: Sử dụng biến môi trường**
```bash
# API key cho NVIDIA AI
export NGC_API_KEY=your_nvidia_api_key_here

# File chứng thực Google Cloud để sử dụng Text-to-Speech
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/google-credentials.json
```

**Tùy chọn 2: Sử dụng file .env (Khuyến nghị)**
Dự án đã có sẵn file `.env.example` làm mẫu. Sao chép file này thành `.env` và điều chỉnh các giá trị:
```bash
# Sao chép file mẫu
cp .env.example .env

# Mở và chỉnh sửa file .env
nano .env  # hoặc mở bằng trình soạn thảo văn bản khác
```

Nội dung của file `.env`:
```
NGC_API_KEY=your_nvidia_api_key_here
GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/google-credentials.json
```

## Cấu trúc thư mục

```
├── prompts/                  # Thư mục chứa các prompt template
│   └── story_to_scene.prompt # Template cho việc chuyển đổi câu chuyện thành cảnh
├── data/                     # Thư mục chứa dữ liệu câu chuyện
│   └── 01/                   # ID của câu chuyện
│       ├── story.txt         # Nội dung câu chuyện
│       ├── scenes.json       # Dữ liệu cảnh được tạo ra
│       ├── video.mp4         # Video tổng hợp từ hình ảnh và âm thanh
│       ├── images/           # Thư mục chứa hình ảnh
│       │   └── scene_1.png   # Hình ảnh cho từng cảnh
│       └── audio/            # Thư mục chứa âm thanh
│           └── scene_1.wav   # File âm thanh cho từng cảnh
├── cached/                   # Thư mục bộ nhớ cache
│   └── llm/                  # Cache cho kết quả LLM
├── bg_music/                 # Thư mục chứa nhạc nền
│   └── Asphyxia.mp3          # File nhạc nền mặc định
├── main.py                   # Mã nguồn chính
├── requirements.txt          # Danh sách các thư viện cần thiết
├── .env                      # File chứa biến môi trường (không được commit lên git)
├── stories.json              # File quản lý danh sách câu chuyện
└── README.md                 # Hướng dẫn
```

## Sử dụng

Đảm bảo bạn đã kích hoạt môi trường ảo trước khi chạy các lệnh:

```bash
# Kích hoạt môi trường (Windows)
.venv\Scripts\activate

# Kích hoạt môi trường (Linux/Mac)
source .venv/bin/activate
```

### Tạo câu chuyện mới

```bash
python main.py --id 01
```

Nếu ID 01 chưa tồn tại, chương trình sẽ yêu cầu bạn nhập nội dung câu chuyện. Nhập nội dung và kết thúc với `Ctrl+D`.

### Liệt kê tất cả các câu chuyện

```bash
python main.py --list
```

### Xử lý lại một câu chuyện hiện có

```bash
python main.py --id 01
```

### Bắt buộc tạo lại các cảnh (không sử dụng bộ nhớ cache)

```bash
python main.py --id 01 --force-scenes
```

### Bắt buộc tạo lại hình ảnh

```bash
python main.py --id 01 --force-images
```

### Bắt buộc tạo lại âm thanh

```bash
python main.py --id 01 --force-audio
```

### Bắt buộc tạo lại video

```bash
python main.py --id 01 --force-video
```

### Sử dụng file nhạc nền khác

```bash
python main.py --id 01 --bg-music path/to/your/music.mp3
```

### Bắt buộc tạo lại tất cả (cảnh, hình ảnh, âm thanh, video)

```bash
python main.py --id 01 --force-scenes --force-images --force-audio --force-video
```

### Bật chế độ debug

```bash
python main.py --id 01 --debug
```

## Sử dụng trong script

Bạn cũng có thể tạo script để tự động hóa các tác vụ:

```bash
#!/bin/bash
# Kích hoạt môi trường ảo
source .venv/bin/activate

# Thiết lập các biến môi trường
export NGC_API_KEY=your_key_here
export GOOGLE_APPLICATION_CREDENTIALS=path/to/credentials.json

# Chạy ứng dụng
python main.py --id 01 --force-video
```

## Format JSON cảnh

Mỗi cảnh được biểu diễn dưới dạng JSON với định dạng sau:

```json
[
  {
    "index": 1,
    "content": "Nội dung của cảnh 1",
    "image_description": "Mô tả ngắn gọn để tạo hình ảnh cho cảnh 1"
  },
  {
    "index": 2,
    "content": "Nội dung của cảnh 2",
    "image_description": "Mô tả ngắn gọn để tạo hình ảnh cho cảnh 2"
  }
]
```

## Cấu trúc quản lý câu chuyện

Các câu chuyện được quản lý trong file `stories.json` với cấu trúc:

```json
{
  "01": {
    "story_id": "01",
    "story_path": "data/01/story.txt",
    "cached_llm_path": "cached/llm/01_1234567890.json",
    "prompt": "prompts/story_to_scene.prompt",
    "images_path": "data/01/images/",
    "audio_path": "data/01/audio/",
    "video_path": "data/01/video.mp4"
  },
  "02": {
    "story_id": "02",
    "story_path": "data/02/story.txt",
    "cached_llm_path": "cached/llm/02_9876543210.json",
    "prompt": "prompts/story_to_scene.prompt",
    "images_path": "data/02/images/",
    "audio_path": "data/02/audio/",
    "video_path": "data/02/video.mp4"
  }
}
```

## Thông tin kỹ thuật

### Quá trình tạo video

Video được tạo ra bằng cách:
1. Sử dụng mỗi hình ảnh như một frame tĩnh
2. Thời lượng hiển thị của mỗi frame được xác định bởi thời lượng của file âm thanh tương ứng
3. Mỗi cảnh trong truyện được ghép từ một hình ảnh và một âm thanh
4. Tất cả các cảnh được ghép lại để tạo thành video hoàn chỉnh
5. Nhạc nền được thêm vào với âm lượng giảm (20% âm lượng gốc)

## Hiệu suất và tối ưu hóa

- Phản hồi từ LLM được lưu vào bộ nhớ cache để tránh phải gọi API lại
- Hình ảnh, âm thanh và video chỉ được tạo một lần trừ khi bạn sử dụng các cờ `--force-*`
- Sử dụng ID để tổ chức và quản lý nội dung hiệu quả

## Khắc phục sự cố

1. **Lỗi môi trường ảo**: Đảm bảo bạn đã kích hoạt môi trường ảo trước khi chạy lệnh
   ```bash
   source .venv/bin/activate  # Linux/Mac
   .venv\Scripts\activate     # Windows
   ```

2. **Lỗi API Key**: Đảm bảo biến môi trường cần thiết đã được thiết lập
   ```bash
   # Sử dụng biến môi trường
   export NGC_API_KEY=your_nvidia_api_key_here
   export GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/google-credentials.json
   
   # Hoặc sử dụng file .env
   # Tạo file .env với nội dung:
   # NGC_API_KEY=your_nvidia_api_key_here
   # GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/google-credentials.json
   ```

3. **Lỗi thiếu thư mục**: Các thư mục cần thiết sẽ được tạo tự động khi bạn chạy chương trình

4. **Lỗi định dạng JSON**: Nếu cấu trúc `stories.json` không đúng định dạng, có thể xóa file để tạo lại từ đầu

5. **Lỗi Google TTS**: Nếu gặp lỗi về giới hạn kích thước text, có thể cần chia nhỏ đoạn văn bản trước khi gửi đến API

6. **Lỗi tạo video**: Đảm bảo có đủ hình ảnh và âm thanh với cùng số thứ tự cảnh, và moviepy đã được cài đặt đúng

## Mở rộng

Bạn có thể mở rộng chương trình bằng cách:

1. Thêm các prompt mới vào thư mục `prompts/`
2. Chỉnh sửa định dạng cảnh trong `prompts/story_to_scene.prompt`
3. Thay đổi các thông số tạo hình ảnh trong hàm `prompt_to_image`
4. Thay đổi giọng đọc trong hàm `text_to_speech` (sử dụng tham số voice_name)
5. Điều chỉnh thông số tạo video trong hàm `create_video_from_scenes` 