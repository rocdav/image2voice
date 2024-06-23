import gradio as gr
from transformers import AutoProcessor, AutoModelForCausalLM
from PIL import Image
import torch
from gtts import gTTS
import spacy
import requests
import nltk.tree
import re
import os

# Carregar o modelo de português do spaCy
nlp = spacy.load("pt_core_news_sm")

# Chave para o LX-Parser
key = "eb159d39469d84f0ff47167a4d89cada"

# Funções de manipulação gramatical
def invert_adj_n(doc, tags):
    frase = []
    already = False
    for i in range(len(doc)):
        if already:
            already = False
            continue
        if doc[i].tag_ != "PUNCT":
            if tags[i] == "A":
                if i + 1 < len(tags) and tags[i + 1] == "N":
                    frase.append(doc[i + 1].text)
                    frase.append(doc[i].text)
                    already = True
                else:
                    frase.append(doc[i].text)
            else:
                frase.append(doc[i].text)
        else:
            frase.append(doc[i].text)
    return frase

def adjust_adj(doc, tags):
    frase = []
    for i in range(len(doc)):
        frase.append(doc[i].text)
        if tags[i] == "A":
            if i + 1 < len(tags) and tags[i + 1] == "A":
                frase.append("e")
    return frase

def adjust_art(doc, tags):
    frase = []
    already = False
    for i in range(len(doc)):
        if already:
            already = False
            continue
        text = doc[i].text
        if tags[i] == "ART" and text.lower() == "a":
            if i + 1 < len(doc):
                gender = doc[i + 1].morph.get("Gender")
                number = doc[i + 1].morph.get("Number")
                if gender and number:
                    if gender[0] == "Masc" and number[0] == "Sing":
                        frase.append("um")
                    elif gender[0] == "Fem" and number[0] == "Sing":
                        frase.append("uma")
                    elif gender[0] == "Masc" and number[0] != "Sing":
                        frase.append("os")
                    else:
                        frase.append("as")
                else:
                    frase.append(text)
            else:
                frase.append(text)
        else:
            frase.append(text)
    return frase

def create_sentence(doc, tags, frase):
    tmp = frase
    for i in range(len(doc)):
        text = doc[i].text
        if doc[i].is_sent_start:
            tmp[i] = tmp[i].capitalize()
        if doc[i].tag_ == "PUNCT":
            tmp[i - 1] += text
    return tmp

def get_productions(texto):
    format = 'parentheses'
    url = "https://portulanclarin.net/workbench/lx-parser/api/"
    request_data = {
        'method': 'parse',
        'jsonrpc': '2.0',
        'id': 0,
        'params': {
            'text': texto,
            'format': format,
            'key': key,
        },
    }
    request = requests.post(url, json=request_data)
    response_data = request.json()
    if "error" in response_data:
        print("Error:", response_data["error"])
        return []
    else:
        result = response_data["result"]
        productions = []
        tree = nltk.tree.Tree.fromstring(result)
        for tag in tree.productions():
            if len(re.findall(r"'.*'", str(tag))) > 0:
                productions.append(str(tag))
        return productions

def get_tags(productions):
    tags = []
    for item in productions:
        if isinstance(item, str):
            tags.append(item[:item.find(' ->')])
        else:
            tags.append(item)
    for item in tags:
        if "'" in item:
            tags.remove(item)
    return tags

def reordenar_sentenca(sentenca):
    if not sentenca.strip():
        return sentenca
    sentenca = sentenca.lower()
    sentence = get_productions(sentenca)
    tags = get_tags(sentence)
    doc = nlp(sentenca)
    if tags[0] != "ART":
        sentenca = "A " + sentenca.strip()
    sentence = get_productions(sentenca)
    tags = get_tags(sentence)
    doc = nlp(sentenca)
    if not sentence:
        return sentenca.strip()
    aux = []
    if len(tags) > 2 and tags[1] == "N" and tags[2] == "N":
        aux = sentenca.split()
        tmp = aux[1]
        aux[1] = aux[2]
        aux.insert(2, "de")
        aux[3] = tmp
        sentenca = " ".join(aux)
        sentence = get_productions(sentenca)
        tags = get_tags(sentence)
        doc = nlp(sentenca)
    frase = []
    already = False
    person = 3
    tmp_doc = []
    for token in doc:
        tmp_doc.append(token)
    frase = invert_adj_n(tmp_doc, tags)
    nova_sentenca = ' '.join(frase)
    productions = get_productions(nova_sentenca)
    tags = get_tags(productions)
    doc = nlp(nova_sentenca)
    while nova_sentenca != sentenca:
        frase = invert_adj_n(doc, tags)
        sentenca = nova_sentenca
        nova_sentenca = ' '.join(frase)
        productions = get_productions(nova_sentenca)
        tags = get_tags(productions)
        doc = nlp(nova_sentenca)
    frase = adjust_adj(doc, tags)
    nova_sentenca = ' '.join(frase)
    productions = get_productions(nova_sentenca)
    tags = get_tags(productions)
    doc = nlp(nova_sentenca)
    while nova_sentenca != sentenca:
        frase = adjust_adj(doc, tags)
        sentenca = nova_sentenca
        nova_sentenca = ' '.join(frase)
        productions = get_productions(nova_sentenca)
        tags = get_tags(productions)
        doc = nlp(nova_sentenca)
    frase = adjust_art(doc, tags)
    sentenca = ' '.join(frase)
    productions = get_productions(sentenca)
    tags = get_tags(productions)
    doc = nlp(sentenca)
    frase = create_sentence(doc, tags, frase)
    sentenca_normalizada = ""
    for i in range(len(frase)):
        sentenca_normalizada += frase[i] + " "
    return sentenca_normalizada.strip()

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

def text_to_speech_gtts(text, lang='pt'):
    tts = gTTS(text=text, lang=lang)
    tts.save("output.mp3")
    return "output.mp3"

# Carregar os modelos
processor = AutoProcessor.from_pretrained("histlearn/microsoft-git-portuguese-neuro-simbolic")
model = AutoModelForCausalLM.from_pretrained("histlearn/microsoft-git-portuguese-neuro-simbolic")

# Configurar o dispositivo (GPU ou CPU)
device = "cuda" if torch.cuda.is_available() else "cpu"
model.to(device)

# Função principal para processar a imagem e gerar a voz
def process_image(image):
    _, pixel_values = prepare_image(image)
    caption_pt = generate_caption(pixel_values)
    sentenca_normalizada = reordenar_sentenca(caption_pt)
    audio_file = text_to_speech_gtts(sentenca_normalizada)
    productions = get_productions(sentenca_normalizada)
    return sentenca_normalizada, productions, audio_file

# Caminhos para as imagens de exemplo
example_image_paths = [
    "example1.jpeg",
    "example2.jpeg",
    "example3.jpeg"
]

# Interface Gradio
iface = gr.Interface(
    fn=process_image,
    inputs=gr.Image(type="filepath"),
    outputs=[gr.Textbox(label="Sentença Normalizada"), gr.Textbox(label="Classes Gramaticais"), gr.Audio(type="filepath", label="Áudio")],
    examples=example_image_paths,
    title="Image to Voice",
    description="Gera uma descrição em português e a converte em voz a partir de uma imagem."
)

if __name__ == "__main__":
    iface.launch()
