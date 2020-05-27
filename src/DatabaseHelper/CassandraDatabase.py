from cassandra.cluster import Cluster
import hashlib
import logging
import uuid
from collections import OrderedDict
import os

class CassandraDatabase:

    def __init__(self):
        logging.basicConfig(level=logging.DEBUG, filename='databasehelper.log')
        __session = None
        __cluster = None
        __feature_mapping = None
        self.read_mapping()
        self.CassandraConnection()
        self.CassandraCreateTables()

    def CassandraConnection(self):
        """
        Connection object for Cassandra
        :return: session, cluster
        """
        db_host_ip = os.getenv('db_host_ip', "127.0.0.1")
        db_port = int(os.getenv('db_port', 9042))
        cass_cluster = Cluster([db_host_ip], port=db_port)
        cass_session = cass_cluster.connect()
        cass_session.execute("""
            CREATE KEYSPACE IF NOT EXISTS mushroomclassifier
            WITH REPLICATION =
            { 'class' : 'SimpleStrategy', 'replication_factor' : 1 }
            """)
        cass_session.set_keyspace('mushroomclassifier')

        self.__session = cass_session
        self.__cluster = cass_cluster

    def CassandraCreateTables(self):
        """Function creates table for User and History and their respective attributes
        """

        self.__session.execute("""
            CREATE TABLE IF NOT EXISTS User (
            id uuid
            , username text
            , password text
            , PRIMARY KEY (id))
            """)

        self.__session.execute("""
            CREATE TABLE IF NOT EXISTS History (
            id uuid
            , label text
            , cap_shape text
            , cap_surface text
            , cap_color text
            , bruises text
            , odor text
            , gill_attachment text
            , gill_spacing text
            , gill_size text
            , gill_color text
            , stalk_shape text
            , stalk_root text
            , stalk_surface_above_ring text
            , stalk_surface_below_ring text
            , stalk_color_above_ring text
            , stalk_color_below_ring text
            , veil_type text
            ,  veil_color text
            , ring_number text
            , ring_type text
            , spore_print_color text
            , population text
            , habitat text
            , user_id text
            , PRIMARY KEY (id))
            """)

    def CheckUserCredentials(self, username, password):
        """Function check if the user exists in the db
        
        Arguments:
            username {[String]}
            password {[sha256 hash string]}
        
        Returns:
            [ResultSet]
        """
        logging.debug("checking credentials username {}".format(str(username)))
        logging.debug("checking credentials password {}".format(str(password)))
        user_lookup_stmt = self.__session.prepare("SELECT * FROM User WHERE username=? and password=? ALLOW FILTERING")
        user = self.__session.execute(user_lookup_stmt, [username, str(password)])
        
        logging.debug(type(user))
        logging.debug(not user)

        return user
    
    def CassandraRegisterUser(self, credentials):
        """Function creates a user if the user doesnt exist
        
        Arguments:
            credentials {[dict]} -- contains username and password in plain text
        
        Returns:
            If user is created, "True", user uuid
            If user was created, "False", None
        """
        password = hashlib.sha256(credentials['password'].encode())
        password = password.hexdigest()
        username = credentials['username']
        user = self.CheckUserCredentials(username, password)
        user_id_uuid = uuid.uuid1()

        logging.debug("registering username {}".format(str(username)))
        logging.debug("registering credentials password {}".format(str(password)))

        if not user:
            user_register_stmt = self.__session.prepare("INSERT INTO User (id, username, password) VALUES (?,?,?)")
            self.__session.execute(user_register_stmt, [user_id_uuid, username, str(password)])
            return "True", user_id_uuid
        
        return "False", None

    def CassandraCheckLoginCredentials(self, credentials):
        """Function checks if user exists
        
        Arguments:
            credentials {[dict]} -- contains username and password in plain text
        
        Returns:
            If user credentials are valid, then "True", user's uuid
            If user credentials are not valid, then "False", None
        """
        password = hashlib.sha256(credentials['password'].encode())
        password = password.hexdigest()
        username = credentials['username']
        user = self.CheckUserCredentials(username, password)

        if user:

            logging.debug("user credentials valid")

            uuid = ""
            for row in user:
                uuid = row.id

            logging.debug("uuid {}".format(str(uuid)))
                
            return "True", uuid
        
        return "False", None

    def CassandraStorePredictions(self, user_uuid, features, prediction):
        """Function inserts features and predicted classification into db
        
        Arguments:
            user_uuid {[uuid1]} -- user's unique id
            features {[dict]} -- user selected options
            prediction {[String]} -- predicted classification
        """
        store_prediction_stmt = self.__session.prepare("INSERT INTO History (id, label, cap_shape, cap_surface, cap_color, bruises,odor, gill_attachment, gill_spacing, gill_size, gill_color, stalk_shape, stalk_root, stalk_surface_above_ring, stalk_surface_below_ring, stalk_color_above_ring, stalk_color_below_ring, veil_type,  veil_color, ring_number, ring_type , spore_print_color, population, habitat, user_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)")
        self.__session.execute(store_prediction_stmt, [uuid.uuid1(), prediction, features['cap-shape'],features['cap-surface'],features['cap-color'],features['bruises'],features['odor'],features['gill-attachment'],features['gill-spacing'],features['gill-size'],features['gill-color'],features['stalk-shape'],features['stalk-root'],features['stalk-surface-above-ring'],features['stalk-surface-below-ring'],features['stalk-color-above-ring'],features['stalk-color-below-ring'],features['veil-type'],features['veil-color'],features['ring-number'],features['ring-type'],features['spore-print-color'],features['population'],features['habitat'], user_uuid])

    def CassandraRetrievePredictionHistory(self, user_uuid):
        """Function retrieves prediction history from db based on user's unique id
        
        Arguments:
            user_uuid {[uuid1]} -- user's unique id
        
        Returns:
            [list] -- dict of features as key and user selected options as values
        """
        prediction_history_stmt = self.__session.prepare("SELECT * FROM History WHERE user_id=? ALLOW FILTERING")
        prediction_history = self.__session.execute(prediction_history_stmt, [user_uuid])
        
        results = []
        for row in prediction_history:
            result = dict(cap_shape=self.__feature_mapping[row.cap_shape],
                cap_surface=self.__feature_mapping[row.cap_surface], 
                cap_color=self.__feature_mapping[row.cap_color], 
                bruises=self.__feature_mapping[row.bruises], 
                odor=self.__feature_mapping[row.odor], 
                gill_attachment=self.__feature_mapping[row.gill_attachment], 
                gill_spacing=self.__feature_mapping[row.gill_spacing], 
                gill_size=self.__feature_mapping[row.gill_size], 
                gill_color=self.__feature_mapping[row.gill_color], 
                stalk_shape=self.__feature_mapping[row.stalk_shape], 
                stalk_root=self.__feature_mapping[row.stalk_root], 
                stalk_surface_above_ring=self.__feature_mapping[row.stalk_surface_above_ring], 
                stalk_surface_below_ring=self.__feature_mapping[row.stalk_surface_below_ring], 
                stalk_color_above_ring=self.__feature_mapping[row.stalk_color_above_ring], 
                stalk_color_below_ring=self.__feature_mapping[row.stalk_color_below_ring], 
                veil_type=self.__feature_mapping[row.veil_type],  
                veil_color=self.__feature_mapping[row.veil_color], 
                ring_number=self.__feature_mapping[row.ring_number], 
                ring_type=self.__feature_mapping[row.ring_type], 
                spore_print_color=self.__feature_mapping[row.spore_print_color], 
                population=self.__feature_mapping[row.population], 
                habitat=self.__feature_mapping[row.habitat], 
                label=row.label)
            results.append(result)

        return results

    def read_mapping(self):
        with open('mapping.txt') as mappings_file:
            lines = mappings_file.readlines()

        feature_attr_mapping = dict()
        for line in lines:
            feature, feature_attrs = line.split(":")[0], line.split(":")[-1].replace(" ", "")
            feature_attrs_list = feature_attrs.split(",")
            for feature_attr in feature_attrs_list:
                feature_attr_key = feature_attr.split("=")[0]
                feature_attr_val = feature_attr.split("=")[-1].replace("\n", "")
                feature_attr_mapping[feature_attr_val] = feature_attr_key

        self.__feature_mapping = feature_attr_mapping