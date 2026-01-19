import factory


class DocumentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "wagtaildocs.Document"

    title = factory.Faker("sentence", nb_words=3)
    file = factory.django.FileField()
