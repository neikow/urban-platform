import faker

fake = faker.Faker()


def paragraph(nb_sentences: int) -> str:
    return fake.paragraph(nb_sentences=nb_sentences)


def title(nb_words: int) -> str:
    return fake.sentence(nb_words=nb_words)


def sentence(nb_words: int) -> str:
    return fake.sentence(nb_words=nb_words)
