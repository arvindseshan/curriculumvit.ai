from flask import Flask, flash, request, render_template 
import google.generativeai as genai
from pypdf import PdfReader
import sys
import requests
from bs4 import BeautifulSoup
from flask_recaptcha import ReCaptcha

API_KEY = "YOUR_API_KEY"
RECAPTCHA_SITE_KEY = "YOUR_RECAPTCHA_SITE_KEY"
RECAPTCHA_SECRET_KEY = "YOUR_RECAPTCHA_SECRET_KEY"

sys_instr=(
       'You are an expert resume analyzer, and your job is to analyze '
       'job descriptions and resumes and provide accurate responses.'
   )
 
app = Flask(__name__)   
app.config['MAX_CONTENT_LENGTH'] = 2 * 1000 * 1000
app.config['RECAPTCHA_SITE_KEY'] = RECAPTCHA_SITE_KEY
app.config['RECAPTCHA_SECRET_KEY'] = RECAPTCHA_SECRET_KEY
app.secret_key = RECAPTCHA_SECRET_KEY
recaptcha = ReCaptcha(app=app)

@app.route('/', methods =["GET", "POST"])
def startup():
    data = {"desc": '', "resp": '', "resume": "", "filename": "",'captcha1':"", 'captcha2':""}
    return render_template("index.html", data = data)

 
@app.route('/response', methods =["GET", "POST"])
def response():
    data = {"desc": '', "resp": '', "resume": "", "filename": "", 'captcha1':"", 'captcha2':""}
    if request.method == "POST":
        desc = request.form.get("desc")
        data["desc"] = desc
        data["filename"] = request.form.get("fname")
        data["resume"] = request.form.get("textcnt")
        
        if recaptcha.verify():
            if not data["resume"]:
                data['captcha1'] = "MISSING FILE"
                return render_template("index.html", data = data)
            if not desc:
                data['captcha2'] = "MISSING JOB DESCRIPTION"
                return render_template("index.html", data = data)

            genai.configure(api_key=API_KEY)

            model=genai.GenerativeModel(
                model_name="gemini-1.5-flash",
                system_instruction=sys_instr)

            if "http" in desc[0:4]:
                desc = requests.get(desc).content
                prompt = f"""Return the readable text from this html for just the job description: ({desc}). Keep the line breaks."""
                response = model.generate_content(prompt)
                desc = response.text
                soup = BeautifulSoup(desc, features="html.parser")

                for script in soup(["script", "style"]):
                    script.extract()

                text = soup.get_text()

                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                desc = '\n'.join(chunk for chunk in chunks if chunk)
                print(f"test http3: {len(desc)}", file=sys.stderr)

            data["desc"] = desc                
            prompt = f"""How well does this resume ({data["resume"]}) match this job description ({desc}). Answer as a percentage and identify the most significant areas of mismatch."""
            response = model.generate_content(prompt)
            resp_text = response.text
            data["resp"] = resp_text
        else:
            data['captcha2'] = "FAILED CAPTCHA VERIFICATION"

    return render_template("index.html", data = data)


@app.route('/upload', methods =["GET", "POST"])
def getfile():
    data = {"resume": '', "filename": '', "captcha1":""}
    if request.method == "POST":
        if recaptcha.verify():
            file = request.files['file']
            if not file:
                data['captcha1'] = "MISSING FILE"
                return render_template("index.html", data = data)
            data["filename"] = file.filename
            reader = PdfReader(file)
            number_of_pages = len(reader.pages)
            full_text = ""
            for i in range(number_of_pages):
                full_text += (reader.pages[i].extract_text() + "\n")
            data["resume"] = full_text
        else:
            data['captcha1'] = "FAILED CAPTCHA VERIFICATION"

    return render_template("index.html", data = data)

 
if __name__=='__main__':
   app.run()