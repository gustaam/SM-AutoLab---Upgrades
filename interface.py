from pathlib import Path
import json
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk

from app import ler_checkpoint, salvar_checkpoint, principal
from config import carregar_configuracoes, salvar_configuracoes, CONFIG_DIR


class App:
    # ...