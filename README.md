How to run it :

pip install with this command :
pip install -r requirements.txt

Install FFmpeg in your computer.

Create a checkpoints folder and
Download these files and add them in the checkpoints folder
https://drive.google.com/drive/u/1/folders/1Fp4sjMi6U3bQaKmQQe04qeXzk7quu0Od

![image](https://github.com/kostas2370/Clippy-V2/assets/96636678/621fa695-5a40-42e0-9464-51aae08d89c7)

After go to the folder clippy run the commands and run those commands:

```shell
py manage.py makemigrations
py manage.py migrate
py manage.py loaddata fixtures/fixtures.json
py manage.py runserver
```

In the end to load some assets like background,intro,outro :
Just go to your browser and put this link :
