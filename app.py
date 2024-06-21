import gradio as gr
from transformers import AutoProcessor, AutoModelForCausalLM, MarianMTModel, MarianTokenizer
from PIL import Image
import torch
import matplotlib.pyplot as plt
from gtts import gTTS
from IPython.display import Audio

# Funções auxiliares
def prepare_image(image_path):
    image = Image.open(image_path).convert("RGB")
    inputs = processor(images=image, return_tensors="pt").to(device)
    return image, inputs.pixel_values

def generate_caption(pixel_values):
    model.eval()
    with torch.no_grad():
        generated_ids = model.generate(
            pixel_values=pixel_values,
            max_length=50,
            num_beams=4,
            early_stopping=True,
            no_repeat_ngram_size=2
        )
    return processor.batch_decode(generated_ids, skip_special_tokens=True)[0]

def translate_to_portuguese(text):
    inputs = translation_tokenizer(text, return_tensors="pt", truncation=True).to(device)
    translated_ids = translation_model.generate(inputs["input_ids"], max_length=50, num_beams=4, early_stopping=True)
    return translation_tokenizer.batch_decode(translated_ids, skip_special_tokens=True)[0]

def text_to_speech_gtts(text, lang='pt'):
    tts = gTTS(text=text, lang=lang)
    tts.save("output.mp3")
    return "output.mp3"

# Carregar os modelos
processor = AutoProcessor.from_pretrained("microsoft/git-large-textcaps")
model = AutoModelForCausalLM.from_pretrained("microsoft/git-large-textcaps")
translation_model_name = 'Helsinki-NLP/opus-mt-tc-big-en-pt'
translation_tokenizer = MarianTokenizer.from_pretrained(translation_model_name)
translation_model = MarianMTModel.from_pretrained(translation_model_name)

# Configurar o dispositivo (GPU ou CPU)
device = "cuda" if torch.cuda.is_available() else "cpu"
model.to(device)
translation_model.to(device)

# Função principal para processar a imagem e gerar a voz
def image_to_voice(image):
    image, pixel_values = prepare_image(image)
    caption_en = generate_caption(pixel_values)
    caption_pt = translate_to_portuguese(caption_en)
    audio_file = text_to_speech_gtts(caption_pt)
    return caption_pt, audio_file

# Interface Gradio
demo = gr.Interface(
    fn=image_to_voice,
    inputs=gr.inputs.Image(type="filepath"),
    outputs=[gr.outputs.Textbox(), gr.outputs.Audio(type="file")],
    title="Image to Voice",
    description="Gera uma descrição em português e a converte em voz a partir de uma imagem."
)

if __name__ == "__main__":
    demo.launch()
