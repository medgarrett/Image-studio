class TrackableObject:
	def __init__(self, objectID, centroid):
		# store the object ID, then initialize a list of centroids
		# using the current centroid
		self.objectID = objectID
		self.centroids = [centroid]
		# initialize a boolean used to indicate if the object has
		# already been counted or not
		self.centroid_5ant = (0,0)
		self.centroid_4ant = (0,0)
		self.centroid_3ant = (0,0)
		self.centroid_2ant = (0,0)
		self.centroid_ant = (0,0)
		self.counted = False
		self.countedsoc = False
		self.ubicacion = 'A'
		self.entro = False
		self.salio = False
		self.vehiculo = None
		self.read = False
		self.nodistsocial = False
		self.movimiento = False
		self.tienecasco = False
		self.countedcasco = False
		
class CountableObject:
	def __init__(self,co_count):
		self.NumCount = co_count
		self.vehiculo = None
		self.entro = False
		self.salio = False
		self.hora = None
		self.imgpath = None
