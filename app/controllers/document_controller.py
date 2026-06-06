import os
import shutil
from sqlalchemy.orm import sessionmaker
from app.models.base import engine
from app.models.schema import Document

Session = sessionmaker(bind=engine)

class DocumentController:
    def __init__(self, documents_dir="data/documents"):
        self.documents_dir = documents_dir
        if not os.path.exists(self.documents_dir):
            os.makedirs(self.documents_dir)

    def add_document(self, documentable_type, documentable_id, source_path):
        session = Session()
        try:
            if not os.path.exists(source_path):
                return False, "Source file does not exist."

            # Create a unique filename to avoid conflicts
            filename = f"{documentable_type}_{documentable_id}_{os.path.basename(source_path)}"
            destination_path = os.path.join(self.documents_dir, filename)

            # Copy the file
            shutil.copy(source_path, destination_path)

            # Create the database record
            new_document = Document(
                file_path=destination_path,
                documentable_id=documentable_id,
                documentable_type=documentable_type
            )
            session.add(new_document)
            session.commit()

            return True, "Document added successfully."
        except Exception as e:
            session.rollback()
            return False, f"An error occurred: {str(e)}"
        finally:
            session.close()

    def delete_document(self, document_id):
        session = Session()
        try:
            document = session.query(Document).get(document_id)
            if not document:
                return False, "Document not found."

            # Remove the file
            if os.path.exists(document.file_path):
                os.remove(document.file_path)

            # Delete the database record
            session.delete(document)
            session.commit()

            return True, "Document deleted successfully."
        except Exception as e:
            session.rollback()
            return False, f"An error occurred: {str(e)}"
        finally:
            session.close()

    def get_documents_for(self, documentable_type, documentable_id):
        session = Session()
        try:
            documents = session.query(Document).filter_by(
                documentable_type=documentable_type,
                documentable_id=documentable_id
            ).all()
            return [{"id": doc.id, "file_path": doc.file_path} for doc in documents]
        finally:
            session.close()
