# Viddie - AI-Powered Video Creation

## Short Description
Viddie is an AI-powered platform for automated video creation, utilizing advanced machine learning models. It streamlines video production by combining GPT-4 for script generation, Conquis TTS for speech synthesis, DALL-E for image generation, and SadTalker for avatar animation. This allows users to generate high-quality videos with minimal manual effort.

## Frontend Repository

[Frontend Repository](https://github.com/kostas2370/video_creator_frontend)
## Sample Videos

- [Demo Video 1](https://www.youtube.com/watch?v=PvrX_jq4fv4)
- [Demo Video 2](https://www.youtube.com/watch?v=bNZvK68O-Rk)

---

## How to Run the Project

There are two ways to run the project: manually or using Docker.

### Manual Installation

#### Prerequisites

- Recommended Python version: 3.9 - 3.11
- Install the following dependencies:
  1. FFmpeg (Required for video rendering) - [Installation Guide](https://phoenixnap.com/kb/ffmpeg-windows)
  2. ImageMagick (Required for subtitles) - [Download](https://imagemagick.org/script/download.php#windows)
  3. eSpeak-NG (Only required for some voice models) - [Download MSI](https://github.com/espeak-ng/espeak-ng/releases)
     - If you don't want to install extra voice packages, use only:
       ```
       tts_models/en/ljspeech/tacotron2-DDC
       ```

#### Installation Steps

1. Navigate to the viddie folder and install dependencies:

   ```shell
   pip install -r requirements/requirements.txt
   ```

2. Create a `checkpoints` folder and download required files from: [Google Drive - Checkpoints](https://drive.google.com/drive/u/1/folders/1Fp4sjMi6U3bQaKmQQe04qeXzk7quu0Od)

3. Inside the viddie folder, create a `.env` file and add the following API keys:

   - `OPEN_API_KEY`
   - `SEARCH_ENGINE_ID`
   - `API_KEY`

   *To find your Google search engine ID and API key, refer to this *[***YouTube Guide***](https://www.youtube.com/watch?v=D4tWHX2nCzQ\&t=127s)*.*

4. Run the following commands to set up the database and start the server:

   ```shell
   py manage.py makemigrations
   py manage.py migrate
   py manage.py loaddata fixtures/fixtures.json
   py manage.py setup_media
   py manage.py runserver
   ```

5. (Optional) To enable ElevenLabs voices, add your `XI_API_KEY` in the `.env` file and run:

   ```shell
   py manage.py setup_elevenlabs
   ```

---

### Docker Installation

1. Create the `.env` file and add your OPEN\_API\_KEY, SEARCH\_ENGINE\_ID, API\_KEY as per `.env_example`.
2. Download and place the required checkpoint files in the `checkpoints` folder from: [Google Drive - Checkpoints](https://drive.google.com/drive/u/1/folders/1Fp4sjMi6U3bQaKmQQe04qeXzk7quu0Od)
3. Navigate to the src folder and run:
   ```shell
   docker-compose up --build
   ```

---

## Admin Panel

- URL: [http://localhost:8000/admin](http://localhost:8000/admin)
- Login Credentials:
  - Username: `admin`
  - Password: `pass`

## API Documentation

You can find all API endpoints in Swagger: [http://localhost:8000/swagger/](http://localhost:8000/swagger/)

---

## Roadmap / To-Do List

- [ ] Convert all `moviepy` functions to `FFmpeg` for better performance.
- [ ] Add **Celery** support for asynchronous and scheduled tasks.
- [ ] Implement unit tests for models, functions, and views.

---

## Contact & Support

For any inquiries or support, feel free to reach out:

- University Email: [kodamia@cs.ihu.gr](mailto:kodamia@cs.ihu.gr)
- Personal Email: [kostas2372@gmail.com](mailto:kostas2372@gmail.com)

---

## Recent Updates

✅ Fixed Conquis TTS Docker issue\
✅ Added support for Gemini and Claude AI models\
✅ Integrated ElevenLabs API voices\
✅ Enabled compilation video creation from Twitch (by game or streamer)\
✅ Added OpenAI voices\
✅ Integrated MidJourney and Stable Diffusion as image providers *(Change providers in ****\`\`****)*\
✅ Dockerized the application for easier deployment

---

