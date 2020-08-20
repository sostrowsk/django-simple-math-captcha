from __future__ import absolute_import
from __future__ import unicode_literals

import base64
import urllib
from io import BytesIO
import random

from PIL import Image, ImageDraw, ImageFont

from django import forms
from django.utils.translation import ugettext_lazy as _

from .utils import hash_answer, get_operator, get_numbers, calculate


class MathCaptchaWidget(forms.MultiWidget):
    template_name = "simplemathcaptcha/captcha.html"

    def __init__(self, start_int=1, end_int=10, question_tmpl=None,
                 question_class=None, attrs=None):
        self.start_int, self.end_int = self.verify_numbers(start_int, end_int)
        self.question_class = question_class or 'captcha-question'
        self.question_tmpl = (
            question_tmpl or _('What is %(num1)i %(operator)s %(num2)i ?'))
        self.question_html = None
        widget_attrs = {'size': '5'}
        widget_attrs.update(attrs or {})
        widgets = (
            # this is the answer input field
            forms.TextInput(attrs=widget_attrs),

            # this is the hashed answer field to compare to
            forms.HiddenInput()
        )
        super(MathCaptchaWidget, self).__init__(widgets, attrs)

    def get_context(self, *args, **kwargs):
        context = super(MathCaptchaWidget, self).get_context(*args, **kwargs)
        context['question_class'] = self.question_class
        context['question_html'] = self.question_html
        return context

    def decompress(self, value):
        return [None, None]

    def render(self, name, value, attrs=None, renderer=None):
        # hash answer and set as the hidden value of form
        hashed_answer = self.generate_captcha()
        value = ['', hashed_answer]

        return super(MathCaptchaWidget, self).render(name, value, attrs=attrs, renderer=renderer)

    def generate_captcha(self):
        # get operator for calculation
        operator = get_operator()

        # get integers for calculation
        x, y = get_numbers(self.start_int, self.end_int, operator)

        # set question to display in output
        self.set_question(x, y, operator)

        # preform the calculation
        total = calculate(x, y, operator)

        return hash_answer(total)

    def set_question(self, x, y, operator):
        # make multiplication operator more human-readable
        question = self.question_tmpl % {
            'num1': x,
            'operator': operator,
            'num2': y
        }

        img = Image.new('RGB', (1, 1), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        text_width, text_height = draw.textsize(question)
        text_width += 2
        img_text = Image.new('RGB', (text_width, text_height), (255, 255, 255))
        draw_text = ImageDraw.Draw(img_text)
        draw_text.text((1, 0), question, fill=(0, 0, 0))
        img_noise = Image.new('RGB', (text_width, text_height), (255, 255, 255))
        draw_noise = ImageDraw.Draw(img_noise)
        for count in range(1, 200):
            draw_noise.point(
                (
                    random.randint(0,text_width),
                    random.randint(0,text_height)
                ),
                fill=(random.randint(0,255),random.randint(0,255),random.randint(0,255))
            )
        for count in range(1, 20):
            draw_noise.line(
                (
                    random.randint(0,text_width),
                    random.randint(0,text_height),
                    random.randint(0,text_width),
                    random.randint(0,text_height)
                ),
                fill=(random.randint(0,255),random.randint(0,255),random.randint(0,255))
            )
        img = Image.blend(img_text, img_noise, 0.2)
        img = img.resize((round(text_width*1.5), round(text_height*1.5)), Image.ANTIALIAS)
        file = BytesIO(img.tobytes())
        img.save(file, format="png")
        file.name = "captcha.png"
        file.seek(0)
        img_src = base64.b64encode(file.read())
        self.question_html = format(urllib.parse.quote(img_src))

    def verify_numbers(self, start_int, end_int):
        start_int, end_int = int(start_int), int(end_int)
        if start_int < 0 or end_int < 0:
            raise Warning('MathCaptchaWidget requires positive integers '
                          'for start_int and end_int.')
        elif end_int < start_int:
            raise Warning('MathCaptchaWidget requires end_int be greater '
                          'than start_int.')
        return start_int, end_int
