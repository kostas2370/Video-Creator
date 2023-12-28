How to run it :

pip install with this command :
pip install -r requirements.txt

Install FFmpeg in your computer (Check this guide : https://phoenixnap.com/kb/ffmpeg-windows)
Install ImageMagick (https://imagemagick.org/script/download.php#windows)
 .

Create a checkpoints folder and
Download these files and add them in the checkpoints folder
https://drive.google.com/drive/u/1/folders/1Fp4sjMi6U3bQaKmQQe04qeXzk7quu0Od

![image](https://github.com/kostas2370/Clippy-V2/assets/96636678/621fa695-5a40-42e0-9464-51aae08d89c7)


Inside the viddie folder : 
Create the .env file and add your OPEN_API_KEY
If you want to enable email services for more custom stuff, you can add these variables :EMAIL_HOST_USER, EMAIL_HOST_PASSWORD

After go to the viddie folder clippy run the commands and run those commands:


```shell
py manage.py makemigrations
py manage.py migrate
py manage.py loaddata fixtures/fixtures.json
py manage.py runserver
```

In the end to load some assets like background,intro,outro :
Just go to your browser and put this link : http://localhost:8000/api/setup/

Login credentials for admin page : username = admin, password = pass


* If you want to create and enable user management - permission you will have to change the permission class from AllowAny to
IsAuthenticated

You can find all the endpoints in swagger : http://localhost:8000/swagger/