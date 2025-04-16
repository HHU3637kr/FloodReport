from pydantic import BaseModel, validator

class KnowledgeBaseCreate(BaseModel):
    name: str
    description: str = ""

    @validator('name')
    def validate_name(cls, name):
        if not name.strip():
            raise ValueError("知识库名称不能为空")
        return name.strip()


class KnowledgeBaseUpdate(KnowledgeBaseCreate):
    pass 