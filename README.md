# pertama create virtual environment dulu dengan command line 

python -m venv stnk_data

# aktifkan terlebih dahulu enviroment virtualnya  dengan enter script di command line

stnk_data\Scripts\Activate


# setelah aktif kemudian jalankan dependensi berikut 

python -m pip install paddlepaddle==3.0.0 -i https://www.paddlepaddle.org.cn/packages/stable/cpu/

diikuti 

pip install "paddlex[base]"

kemudian 

pip install "paddlex[ocr]". 

jika tidak terdapat error bisa di lanjutkan untuk install

pip install -r requirements.txt

setelah itu untuk memulai menjalankan program bisa ketik command 

fastapi dev
