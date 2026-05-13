# AI-TTS-Respond V1

## Install AI TTS Respond

**Step 1**: Install PyTorch

Choose **one** of the following methods: **pip**

<details>
<summary>NVIDIA GPU</summary>

```bash
# Install pytorch with your CUDA version, e.g.
pip install torch==2.8.0+cu128 torchaudio==2.8.0+cu128 --extra-index-url https://download.pytorch.org/whl/cu128
```
> See [PyTorch official site](https://pytorch.org/get-started/locally/) for other versions installation.

</details>

<details>
<summary>CPU</summary>

```bash
pip install torch==2.8.0 torchaudio==2.8.0
```
</details>

**Step 2**: Download AI TTS Respond

```bash
git clone https://github.com/Spacetrale/AI-TTS-Respond.git
cd AI-TTS-Respond
python -m venv ai-tts-respond
./ai-tts-respond/Scripts/activate
pip install -r requirements.txt
```

**Step 3**: Run it

```bash
python main.py
```
