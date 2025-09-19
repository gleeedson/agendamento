from http import HTTPStatus

from fastapi import FastAPI

from agendamento.schemas import Message

app = FastAPI(title='API de agendamentos')


@app.get('/', status_code=HTTPStatus.OK, response_model=Message)
def read_root():
    return {'message': 'Olá Mundo!'}
