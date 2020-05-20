#!/usr/bin/python3
"""
This file is used for execution of back end server.

Author: xkloco00@stud.fit.vutbr.cz
"""
from app import app

if __name__ == '__main__':
    app.run(port=42024, host='0.0.0.0')
