import uuid

from pydantic import BaseModel, field_serializer
import sqlalchemy as db
from .ConnectionString import ConnectionString, DEFAULT_DB


class NewConfigurationTemplate(BaseModel):
    TemplateID: str = ''
    Subnet: str = ''
    ListenPortStart: int = 0
    ListenPortEnd: int = 0
    Notes: str = ""
    
class NewConfigurationTemplates:
    def __init__(self):
        self.engine = db.create_engine(ConnectionString(DEFAULT_DB))
        self.metadata = db.MetaData()
        self.templatesTable = db.Table(
            'NewConfigurationTemplates', self.metadata,
            db.Column('TemplateID', db.String(255), primary_key=True),
            db.Column('Subnet', db.String(255)),
            db.Column('ListenPortStart', db.Integer),
            db.Column('ListenPortEnd', db.Integer),
            db.Column('Notes', db.Text),
        )
        self.metadata.create_all(self.engine)
        self.Templates: list[NewConfigurationTemplate] = []
        self.__getTemplates()
        
    def GetTemplates(self):
        self.__getTemplates()
        return list(map(lambda x : x.model_dump(), self.Templates))
    
    def __getTemplates(self):
        with self.engine.connect() as conn:
            templates = conn.execute(
                self.templatesTable.select()
            ).mappings().fetchall()
            self.Templates.clear()
            self.Templates = [NewConfigurationTemplate(**template) for template in templates]
    
    def CreateTemplate(self) -> NewConfigurationTemplate:
        return NewConfigurationTemplate(TemplateID=str(uuid.uuid4()))
    
    def SearchTemplate(self, template: NewConfigurationTemplate):
        try:
            first = next(filter(lambda x : x.TemplateID == template.TemplateID, self.Templates))
        except StopIteration:
            return None
        return first
    
    def UpdateTemplate(self, template: dict[str, str]) -> tuple[bool, str] | tuple[bool, None]:
        try:
            template = NewConfigurationTemplate(**template)
            with self.engine.begin() as conn:
                if self.SearchTemplate(template):
                    conn.execute(
                        self.templatesTable.update().values(
                            template.model_dump(exclude={'TemplateID'})
                        ).where(
                            self.templatesTable.c.TemplateID == template.TemplateID
                        )
                    )
                else:
                    conn.execute(
                        self.templatesTable.insert().values(
                            template.model_dump()
                        )
                    )
            self.__getTemplates()
        except Exception as e:
            return False, str(e)
        return True, None
    
    def DeleteTemplate(self, template: dict[str, str]) -> tuple[bool, str] | tuple[bool, None]:
        try:
            template = NewConfigurationTemplate(**template)
            with self.engine.begin() as conn:
                conn.execute(
                    self.templatesTable.delete().where(
                        self.templatesTable.c.TemplateID == template.TemplateID
                    )
                )
            self.__getTemplates()
        except Exception as e:
            return False, str(e)
        return True, None