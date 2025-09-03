class RepositoryExample:

    def __init__(self, entity_manager: any):
        self.entity_manager = entity_manager

    def save(self, data:any):
        self.entity_manager.save(data)
        # print(f"Saving {data}...")

    def get(self, id:str):
        return self.entity_manager.get(id)
        # print(f"Getting {id}...")