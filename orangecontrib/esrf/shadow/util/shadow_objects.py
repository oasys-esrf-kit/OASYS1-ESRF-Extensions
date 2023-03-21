class ConicCoefficientsPreProcessorData:
    def __init__(self,
                conic_coefficient_0=0.0,
                conic_coefficient_1=0.0,
                conic_coefficient_2=0.0,
                conic_coefficient_3=0.0,
                conic_coefficient_4=0.0,
                conic_coefficient_5=0.0,
                conic_coefficient_6=0.0,
                conic_coefficient_7=0.0,
                conic_coefficient_8=0.0,
                conic_coefficient_9=0.0,
                source_plane_distance    = None,
                image_plane_distance     = None,
                angles_respect_to        = None,
                incidence_angle_deg      = None,
                reflection_angle_deg     = None,
                mirror_orientation_angle = None,
                title="",
                 ):
        self.conic_coefficient_0 = conic_coefficient_0
        self.conic_coefficient_1 = conic_coefficient_1
        self.conic_coefficient_2 = conic_coefficient_2
        self.conic_coefficient_3 = conic_coefficient_3
        self.conic_coefficient_4 = conic_coefficient_4
        self.conic_coefficient_5 = conic_coefficient_5
        self.conic_coefficient_6 = conic_coefficient_6
        self.conic_coefficient_7 = conic_coefficient_7
        self.conic_coefficient_8 = conic_coefficient_8
        self.conic_coefficient_9 = conic_coefficient_9


        self.source_plane_distance    = source_plane_distance
        self.image_plane_distance     = image_plane_distance
        self.angles_respect_to        = angles_respect_to
        self.incidence_angle_deg      = incidence_angle_deg
        self.reflection_angle_deg     = reflection_angle_deg
        self.mirror_orientation_angle = mirror_orientation_angle
        self.title = title