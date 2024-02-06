Frontend Demo repository :  https://github.com/kostas2370/ViddieDEMO

How to run it :
Recommended python version : 3.9 - 3.11

First install these 2 programs in your computer : 


1. Install FFmpeg in your computer (Check this guide : https://phoenixnap.com/kb/ffmpeg-windows) (For video Rendering)
2. Install ImageMagick (https://imagemagick.org/script/download.php#windows) (For subtitles)
3. For some voice model you will need to install the MSI from here (https://github.com/espeak-ng/espeak-ng/releases)

If you dont want to install any extra packages for voices , 
use only : tts_models/en/ljspeech/tacotron2-DDC Model

Go to the viddie folder and run this command :
pip install -r requirements.txt


Create a checkpoints folder and
Download these files and add them in the checkpoints folder
https://drive.google.com/drive/u/1/folders/1Fp4sjMi6U3bQaKmQQe04qeXzk7quu0Od

![image](https://github.com/kostas2370/Clippy-V2/assets/96636678/621fa695-5a40-42e0-9464-51aae08d89c7)


Inside the viddie folder : 
Create the .env file and add your OPEN_API_KEY, SEARCH_ENGINE_ID, API_KEY 

To find your google search_engine_id and api_key , check this guide : https://www.youtube.com/watch?v=D4tWHX2nCzQ&t=127s

After go to the viddie folder and run those commands:

```shell
py manage.py makemigrations
py manage.py migrate
py manage.py loaddata fixtures/fixtures.json
py manage.py setup_media
py manage.py runserver
```

Login credentials for admin page : username = admin, password = pass


You can find all the endpoints in swagger : http://localhost:8000/swagger/

* TO DO :
1. Add voice cloning for avatars
2. Better Image Selection in web mode
3. Convert all moviepy functions to ffmpeg for better Performance .
4. Test Cases for models, functions and Views
5. Improvement in dall e prompt , mcore detailed prompts for more consistency
6. Support for OPENAI tts

For any Injuries or Support you can contact me at those emails :
1. kodamia@cs.ihu.gr (University Email)
2. kostas2372@gmail.com (Personal Email)
