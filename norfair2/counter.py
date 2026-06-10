#contador de vahiculos
from numpy.testing._private.utils import integer_repr
from norfair2.trackableobject import TrackableObject
from typing import Optional, Sequence, Tuple
from norfair2.drawing import centroid

try:
    import cv2
except ImportError:
    from .utils import DummyOpenCVImport

    cv2 = DummyOpenCVImport()
import random

import numpy as np

from .utils import validate_points

def counter_tracked_objects(
    frame: np.array,
    objects: Sequence["TrackedObject"],
    rect_entrada: np.array,
    trackableObjects = {} ,
    co_count = int,
    Carpeta_temp = str
    ):

    alt_max_camioneta = 70
    contador = 0
    imgpath = ''
    for obj in objects:
        if not obj.live_points.any():
            continue
        id_centroid = centroid(obj.estimate[obj.live_points])
        #print(str(id_centroid))
        objectID = obj.id


        # puntos para sacar altura del recuadro

        points = obj.estimate
        points = points.astype(int)
        altura_bbox = points[1][1]-points[0][1]
        #print(str(points[1][1]-points[0][1]))
        y = points[0][1]
        h = points[1][1] - y
        x = points[0][0]
        w = points[1][0] - x        
        delta = 15


	# Checkea si existe trackableObject para el actual
	# object ID
        to = trackableObjects.get(objectID, None)
	# Si no existe, se crea uno
        if to is None:
            to = TrackableObject(objectID, id_centroid)
            

	# Si existe lo utilizo para verificar si ingresa o sale
        else:
            
            if not to.counted:
		
			#Ingresa en la zona B, color amarilla. Si antes estaba en la zona C entonces Salio
                if (id_centroid[0]>rect_entrada[4] and id_centroid[0]<(rect_entrada[4]+rect_entrada[6] )and (id_centroid[1]>rect_entrada[5] and id_centroid[1]<(rect_entrada[5]+rect_entrada[7] ))) :
                    if to.ubicacion == 'C':
                        to.counted = True
                        to.salio = True
                        if altura_bbox < alt_max_camioneta:
                            to.vehiculo = 'Camioneta'
                        if altura_bbox >= alt_max_camioneta:
                            to.vehiculo = 'Maquinaria'
                        

                        
                        result=frame[y-delta:y+h+delta, x-delta:x+w+delta]
                        #Obtener color mas frecuente bbox
                        hsv = cv2.cvtColor(result, cv2.COLOR_BGR2HSV)
                        colors, count = np.unique(hsv.reshape(-1, hsv.shape[-1]), axis=0, return_counts=True)
                        #colors, count = np.unique(hsv.reshape(-1, hsv.shape[-1]), axis=0, return_counts=True)
                        #print(colors[np.argsort(-count)][:5])
                        
                        imgpath = Carpeta_temp + '/' + str(co_count)+'_'+str(to.objectID)+".png"
                        cv2.imwrite(imgpath,result)
                        to.imgpath = imgpath
                        to.ubicacion = 'B'

                    # Si estaba en la zona A se cambia a ubicacion B
                    if to.ubicacion == 'A':		
                        to.ubicacion = 'B'

		#Verifico si ingresa al rectangulo
                elif (id_centroid[0] > rect_entrada[0] and id_centroid[0] < (rect_entrada[0] + rect_entrada[2]) and (id_centroid[1] > rect_entrada[1] and id_centroid[1] < (rect_entrada[1] + rect_entrada[3]))):
                    if to.ubicacion == 'B':
                        to.counted = True
                        to.entro = True
                        if altura_bbox < alt_max_camioneta:
                            to.vehiculo = 'Camioneta'
                        if altura_bbox >= alt_max_camioneta:
                            to.vehiculo = 'Maquinaria'
                        
                        result=frame[y-delta:y+h+delta, x-delta:x+w+delta]
                        #Obtener color mas frecuente bbox
                        hsv = cv2.cvtColor(result, cv2.COLOR_BGR2HSV)
                        colors, count = np.unique(hsv.reshape(-1, hsv.shape[-1]), axis=0, return_counts=True)
                        print(colors[np.argsort(-count)][:5])
                        
                        imgpath = Carpeta_temp + '/' + str(co_count)+'_'+str(to.objectID)+".png"
                        cv2.imwrite(imgpath,result)
                        to.imgpath = imgpath
                    



                    # Si estaba en la zona A se cambia a ubicacion B
                    if to.ubicacion == 'A':
                        to.ubicacion = 'C'

                # si esta en la zona A se resetea todos los valores por si vuelve a salir
                else :
                    to.ubicacion = 'A'
                    to.counted = False
                    to.vehiculo = None
                    to.entro = False
                    to.salio = False
                    to.read = False
        


        trackableObjects[objectID] = to
    return trackableObjects, frame

#counter objects personas
def counter_tracked_objectsV2(
    frame: np.array,
    objects: Sequence["TrackedObject"],
    rect_entrada: np.array,
    trackableObjects = {} ,
    co_count = int,
    Carpeta_temp = str,
    detections_casco = [],
    Confidence_casco = int
    ):

    
    contador = 0
    imgpath = ''
    for obj in objects:
        if not obj.live_points.any():
            continue
        id_centroid = centroid(obj.estimate[obj.live_points])
        #print(str(id_centroid))
        objectID = obj.id


        # puntos para sacar altura del recuadro

        points = obj.estimate
        points = points.astype(int)
        altura_bbox = points[1][1]-points[0][1]
        #print(str(points[1][1]-points[0][1]))
        y = points[0][1]
        h = points[1][1] - y
        x = points[0][0]
        w = points[1][0] - x        
        delta = 7

        #radio en metros
        radio_mts = 2
        #cnversion radio de mts a px
        mts2px = 80# para video de personas caminando 40
        radio_px = radio_mts*mts2px
        y_ratio = 4
        #pixeles para considerar movimiento
        movpx = 10 #1 para personas caminando
	# Checkea si existe trackableObject para el actual
	# object ID
        to = trackableObjects.get(objectID, None)
	# Si no existe, se crea uno
        if to is None:
            to = TrackableObject(objectID, id_centroid)
            

	# Si existe lo utilizo para verificar si ingresa o sale
        else:
            
            if not to.counted:
		
			#Ingresa en la zona B, color amarilla. Si antes estaba en la zona C entonces Salio
                if (id_centroid[0]>rect_entrada[4] and 
                id_centroid[0]<(rect_entrada[4]+rect_entrada[6] )and 
                (id_centroid[1]>rect_entrada[5] and 
                id_centroid[1] < (rect_entrada[5]+rect_entrada[7] ))) :

                    if to.ubicacion == 'C':
                        to.counted = True
                        to.salio = True
                        to.vehiculo = 'Persona'
                        
                        

                        
                        result=frame[y-delta:y+h+delta, x-delta:x+w+delta]
                        #Obtener color mas frecuente bbox
                        hsv = cv2.cvtColor(result, cv2.COLOR_BGR2HSV)
                        colors, count = np.unique(hsv.reshape(-1, hsv.shape[-1]), axis=0, return_counts=True)
                        #colors, count = np.unique(hsv.reshape(-1, hsv.shape[-1]), axis=0, return_counts=True)
                        #print(colors[np.argsort(-count)][:5])
                        
                        imgpath = Carpeta_temp + '/' + str(co_count)+'_'+str(to.objectID)+".png"
                        cv2.imwrite(imgpath,result)
                        to.imgpath = imgpath
                        to.ubicacion = 'B'

                    # Si estaba en la zona A se cambia a ubicacion B
                    if to.ubicacion == 'A':		
                        to.ubicacion = 'B'

		#Verifico si ingresa al rectangulo
                elif (id_centroid[0] > rect_entrada[0] and 
                id_centroid[0] < (rect_entrada[0] + rect_entrada[2]) and 
                (id_centroid[1] > rect_entrada[1] and 
                id_centroid[1] <= (rect_entrada[1] + rect_entrada[3]))):

                    if to.ubicacion == 'B':
                        to.counted = True
                        to.entro = True
                        to.vehiculo = 'Persona'
                        
                        
                        result=frame[y-delta:y+h+delta, x-delta:x+w+delta]
                        #Obtener color mas frecuente bbox
                        hsv = cv2.cvtColor(result, cv2.COLOR_BGR2HSV)
                        colors, count = np.unique(hsv.reshape(-1, hsv.shape[-1]), axis=0, return_counts=True)
                        print(colors[np.argsort(-count)][:5])
                        
                        imgpath = Carpeta_temp + '/' + str(co_count)+'_'+str(to.objectID)+".png"
                        cv2.imwrite(imgpath,result)
                        to.imgpath = imgpath
                    



                    # Si estaba en la zona A se cambia a ubicacion B
                    if to.ubicacion == 'A':
                        to.ubicacion = 'C'

                # si esta en la zona A se resetea todos los valores por si vuelve a salir
                else :
                    to.ubicacion = 'A'
                    to.counted = False
                    to.vehiculo = None
                    to.entro = False
                    to.salio = False
                    to.read = False

#-----------------#verifico distanciamiento social------------------------
            to.countedsoc = False
            to.nodistsocial = False
            #Recorro todos los demas objetos y verifico dist soc
            for objsoc in objects:
                if  objsoc.live_points.any():
                     
                    id_centroidsoc = centroid(objsoc.estimate[objsoc.live_points])
                    # Condicion vecino dentro de cuadraodo 2 radio
                    if not (id_centroidsoc == id_centroid):
                        if not to.countedsoc :
                            if ((id_centroid[0] - radio_px) < id_centroidsoc[0] and 
                            (id_centroid[0] + radio_px) > id_centroidsoc[0] and 
                            (id_centroid[1] - radio_px/y_ratio) < id_centroidsoc[1] and 
                            (id_centroid[1] + radio_px/y_ratio) > id_centroidsoc[1] ):
                                to.countedsoc = True
                                to.nodistsocial = True

##------------------#Verifico si esta en movimiento 


            if not ((id_centroid[0] + movpx ) >= to.centroid_5ant[0] and 
            (id_centroid[0] - movpx ) <= to.centroid_5ant[0] and 
            (id_centroid[1] + movpx ) >= to.centroid_5ant[1] and 
            (id_centroid[1] - movpx ) <= to.centroid_5ant[1] ) :
                to.movimiento = True
            
            if  ((id_centroid[0] + movpx ) >= to.centroid_5ant[0] and 
            (id_centroid[0] - movpx ) <= to.centroid_5ant[0] and 
            (id_centroid[1] + movpx ) >= to.centroid_5ant[1] and 
            (id_centroid[1] - movpx ) <= to.centroid_5ant[1] ) :
                to.movimiento = False
            
            
        ##------Guardo posicion centroide anterior   
            to.centroid_5ant = to.centroid_4ant
            to.centroid_4ant = to.centroid_3ant
            to.centroid_3ant = to.centroid_2ant
            to.centroid_2ant = to.centroid_ant 
            to.centroid_ant = id_centroid

        #--------Verifico si tiene casco
            print('antes detections casco')
            if detections_casco is not None :# and len(detections_casco) >= 1:
               
                for i in range(len(detections_casco) ) :
                    
                    #Verifico si la persona detecta casco o cabeza
                    if detections_casco[i].points[1] > y and detections_casco[i].points[1] < y + int(h/2) and detections_casco[i].points[0] > x and detections_casco[i].points[0] < x + w :
                        print('entre if casco')
                    #verifico si tiene casco y su confidencia. multiplico *100 para pasar de 0-1 a 0-100
                        if detections_casco[i].data == 0 and detections_casco[i].scores*100 > Confidence_casco: 
                            to.tienecasco = True
                            to.countedcasco = True

                        if detections_casco[i].data == 1 : 
                            to.tienecasco = False   
                            to.countedcasco = True

                    cv2.circle(frame,(int(detections_casco[i].points[0]),int(detections_casco[i].points[1])),6,(0,255,0),2)
                    #cv2.rectangle(frame,(x-5,y-5),(int(x + w + 5)  , int(y + h/3)),color=(0,255,0),thickness=3 )




        trackableObjects[objectID] = to
    return trackableObjects, frame




def stat_frame (
    frame: np.array,
    objects: Sequence["TrackedObject"],
    trackableObjects = {}, 
    H =  float ):

 #-----------Inicio contador i de in (entrada) y o de out (salida)-----------------
    ing = 0
    out = 0
    disoc = 0
    nodisoc = 0
    mov = 0
    nomov = 0
    usacasco = 0
    nocasco = 0

    print('inicializo contadores')
    for ob in trackableObjects:
        print('ID:', str(trackableObjects[ob].objectID),' Salio: ', str(trackableObjects[ob].salio), ' Entro: ', str(trackableObjects[ob].entro))

    for ob in trackableObjects:

    #Contavilizo pasan por la linea    
        if trackableObjects[ob].salio == True:
            out = out + 1
        
        if trackableObjects[ob].entro == True:
            ing = ing + 1
            print('cuento entrada')            


    for obj in objects:
        if not obj.live_points.any():
            continue
        id_centroid = centroid(obj.estimate[obj.live_points])
        #print(str(id_centroid))
        objectID = obj.id
    
        tob = trackableObjects.get(objectID, None)
    
    #Contavilizo personas que cumplen uso casco 
        if tob.countedcasco == True:
            if tob.tienecasco == True:
                usacasco = usacasco + 1

            if tob.tienecasco == False:
                nocasco = nocasco + 1

    
    
    
        #Contavilizo personas que cumplen distanciamiento social 
        if tob.nodistsocial == True:
            nodisoc = nodisoc + 1

        if tob.nodistsocial == False:
            disoc = disoc + 1

    #Contavilizo personas en movimiento
        if tob.movimiento == True:
            mov = mov + 1

        if tob.movimiento == False:
            nomov = nomov + 1


    info_total = [
        ("No cumple dist. social", nodisoc),
        ("Cumple dist. social", disoc),
        ("Cruzo linea. Se Aleja", ing),
        ("Cruzo linea. Se acerca", out),
        ("Persona Movimiento", mov),
        ("Persona quieta", nomov),
        ("Persona usa casco", usacasco),
        ("Persona no usa casco", nocasco)
    ]
    info = [
        ("No cumple dist. social", nodisoc),
        ("Cumple dist. social", disoc),
        ("Persona Movimiento", mov),
        ("Persona quieta", nomov),
        ("Persona usa casco", usacasco),
        ("Persona no usa casco", nocasco)
    ]


    colortext_total = [
        (0,0,255),
        (0,128,0),
        (255, 0, 255),
        (255, 0, 255),
        (255,0,0),
        (0, 255, 0),
        (0, 255, 0),
        (0,0,255)
    ]
    colortext = [
        (0,0,255),
        (0,128,0),
        (255,0,0),
        (0, 255, 0),
        (0, 255, 0),
        (0,0,255)
    ]
    # loop over the info tuples and draw them on our frame
    for (i, (k, v)) in enumerate(info):
        text = "{}: {}".format(k, v)
        cv2.putText(frame, text, (10, 720 - ((i * 30) + 100)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, colortext[i], 2)
    # check to see if we should write the frame to disk
    cv2.putText(frame, 'COMPUTER VISION', (10, 720 - (((i + 2) * 30) + 100)),
    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2) 
    cv2.putText(frame, 'Ejemplo de aplicacion:', (10, 720 - (((i + 1) * 30) + 100)),
    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

    return frame




def proximidad_entrada(objects: Sequence["TrackedObject"],
                        framerate_analisis : int,
                        framerate_rapido: int,
                        rect_analisis: np.array,):

    i=0
    for obj in objects:
        if not obj.live_points.any():
            return framerate_rapido
            continue
        id_centroid = centroid(obj.estimate[obj.live_points])
        if (id_centroid[0] > rect_analisis[0] and id_centroid[0] < (rect_analisis[0] + rect_analisis[2]) and (id_centroid[1] > rect_analisis[1] and id_centroid[1] < (rect_analisis[1] + rect_analisis[3]))):
            i = i + 1
        
    
    if i == 0 :
        return framerate_rapido
    elif i > 0 :
        return framerate_analisis


