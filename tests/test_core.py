from types import SimpleNamespace

from subtitulador.core import agrupar_subtitulos, es_audio, format_time, mapear


def palabra(texto, inicio, fin):
    return SimpleNamespace(word=texto, start=inicio, end=fin)


def segmento(*palabras):
    return SimpleNamespace(words=list(palabras))


def test_format_time_formato_srt():
    assert format_time(0) == "00:00:00,000"
    assert format_time(3725.5) == "01:02:05,500"


def test_format_time_no_produce_milisegundos_de_1000():
    assert format_time(1.9999) == "00:00:02,000"


def test_mapear_dentro_del_intervalo():
    assert mapear(5.0, [(4.0, 6.0)], [0.0]) == 1.0


def test_mapear_en_silencio_usa_inicio_del_siguiente_tramo():
    intervalos, offsets = [(4.0, 6.0), (8.0, 10.0)], [0.0, 2.0]
    assert mapear(3.0, intervalos, offsets) == 0.0
    assert mapear(9.0, intervalos, offsets) == 3.0


def test_mapear_despues_del_ultimo_tramo():
    assert mapear(11.0, [(4.0, 6.0), (8.0, 10.0)], [0.0, 2.0]) == 4.0


def test_agrupar_respeta_maximo_de_palabras():
    seg = segmento(palabra("uno", 0.0, 0.2), palabra("dos", 0.3, 0.5),
                   palabra("tres", 0.6, 0.8), palabra("cuatro", 0.9, 1.1),
                   palabra("cinco", 1.2, 1.4))
    bloques = agrupar_subtitulos([seg], 3)
    assert [len(b) for b in bloques] == [3, 2]


def test_agrupar_parte_por_pausa_larga():
    seg = segmento(palabra("hola", 0.0, 0.3), palabra("mundo", 1.5, 1.8))
    bloques = agrupar_subtitulos([seg], 5)
    assert [len(b) for b in bloques] == [1, 1]


def test_agrupar_parte_por_puntuacion_final():
    seg = segmento(palabra("Hola.", 0.0, 0.3), palabra("mundo", 0.35, 0.6))
    bloques = agrupar_subtitulos([seg], 5)
    assert [len(b) for b in bloques] == [1, 1]


def test_es_audio_ignora_mayusculas():
    assert es_audio("cancion.MP3")
    assert not es_audio("video.mp4")
