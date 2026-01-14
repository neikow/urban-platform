import factory
from .models import PedagogyCardPage


class PedagogyCardPageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PedagogyCardPage

    title = factory.Faker("sentence", nb_words=4)
    # Using a simple text for RichTextField (it usually accepts string/html)
    body = factory.Faker("paragraph", nb_sentences=10)

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """
        Custom create method to handle Wagtail's tree structure.
        Expects a 'parent' argument to attach the page to.
        """
        parent = kwargs.pop("parent", None)

        # Create the instance in memory
        instance = model_class(**kwargs)

        if parent:
            # Add to the tree using add_child() which saves the instance
            parent.add_child(instance=instance)
            return instance

        raise ValueError(
            "Headless page creation not supported by this factory. Please provide a 'parent' argument."
        )
