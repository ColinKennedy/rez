class Singularity(object):
    @staticmethod
    def name():
        return "singularity"

    @staticmethod
    def get_pre_command(image):
        return "singularity exec {image}".format(image=image)


def register_plugin():
    return Singularity
