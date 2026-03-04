# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/neikow/urban-platform/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                           |    Stmts |     Miss |   Branch |   BrPart |      Cover |   Missing |
|--------------------------------------------------------------- | -------: | -------: | -------: | -------: | ---------: | --------: |
| core/\_\_init\_\_.py                                           |        0 |        0 |        0 |        0 |    100.00% |           |
| core/apps.py                                                   |        4 |        0 |        0 |        0 |    100.00% |           |
| core/blocks.py                                                 |      175 |        4 |        0 |        0 |     97.71% |   240-250 |
| core/context\_processors.py                                    |        6 |        0 |        0 |        0 |    100.00% |           |
| core/emails/\_\_init\_\_.py                                    |        0 |        0 |        0 |        0 |    100.00% |           |
| core/emails/services.py                                        |       48 |        2 |        2 |        0 |     96.00% |   26, 112 |
| core/emails/tasks.py                                           |       66 |       10 |        4 |        0 |     85.71% |44-48, 81-85 |
| core/emails/tokens.py                                          |       27 |        0 |        0 |        0 |    100.00% |           |
| core/management/\_\_init\_\_.py                                |        0 |        0 |        0 |        0 |    100.00% |           |
| core/models/\_\_init\_\_.py                                    |        6 |        0 |        0 |        0 |    100.00% |           |
| core/models/city.py                                            |        5 |        1 |        0 |        0 |     80.00% |         8 |
| core/models/city\_district.py                                  |       10 |        0 |        0 |        0 |    100.00% |           |
| core/models/city\_neighborhood.py                              |       15 |        2 |        0 |        0 |     86.67% |    18, 22 |
| core/models/email\_event.py                                    |       27 |        0 |        0 |        0 |    100.00% |           |
| core/models/neighborhood\_association.py                       |       13 |        1 |        0 |        0 |     92.31% |        26 |
| core/models/user.py                                            |       57 |        4 |        6 |        3 |     88.89% |22, 38, 40, 114 |
| core/sitemaps.py                                               |       62 |       16 |        4 |        0 |     69.70% |29-31, 34, 37, 45, 53-63, 71, 79, 87, 95, 103 |
| core/templatetags/\_\_init\_\_.py                              |        0 |        0 |        0 |        0 |    100.00% |           |
| core/templatetags/custom\_blocks.py                            |       18 |       11 |        8 |        0 |     26.92% |10-19, 24-39 |
| core/templatetags/forms.py                                     |        6 |        0 |        0 |        0 |    100.00% |           |
| core/templatetags/navigation\_tags.py                          |       43 |        2 |       14 |        3 |     91.23% |21->24, 35, 57 |
| core/templatetags/structured\_data.py                          |      112 |        6 |       42 |       15 |     86.36% |30-31, 90->93, 100, 125->128, 129->132, 133->138, 135->138, 139, 141, 154->157, 158->161, 162->165, 166->169, 173->189, 181->187, 200 |
| core/toc.py                                                    |       41 |        1 |       22 |        1 |     96.83% |        52 |
| core/utils.py                                                  |        6 |        0 |        2 |        0 |    100.00% |           |
| core/views/\_\_init\_\_.py                                     |        0 |        0 |        0 |        0 |    100.00% |           |
| core/views/auth\_mixins.py                                     |       29 |        0 |       10 |        0 |    100.00% |           |
| core/views/email\_verify.py                                    |       24 |        0 |        4 |        0 |    100.00% |           |
| core/views/login.py                                            |       34 |        1 |       10 |        1 |     95.45% |        57 |
| core/views/logout.py                                           |        8 |        0 |        0 |        0 |    100.00% |           |
| core/views/me.py                                               |        9 |        0 |        0 |        0 |    100.00% |           |
| core/views/password\_reset.py                                  |       70 |        4 |       10 |        3 |     91.25% |67, 80, 103-104, 109->114 |
| core/views/profile\_edit.py                                    |      117 |        6 |       24 |        6 |     91.49% |61, 71, 75, 104, 114, 121 |
| core/views/register.py                                         |       78 |       10 |       18 |        7 |     82.29% |66, 79, 85, 92, 94, 96, 107-109, 151 |
| core/wagtail\_hooks.py                                         |       79 |        5 |       12 |        6 |     87.91% |59->74, 122, 157, 159, 161, 163 |
| core/widgets.py                                                |       45 |       19 |       16 |        3 |     47.54% |16, 28-35, 49, 68-71, 81-88, 98 |
| home/\_\_init\_\_.py                                           |        0 |        0 |        0 |        0 |    100.00% |           |
| home/apps.py                                                   |        4 |        0 |        0 |        0 |    100.00% |           |
| home/management/\_\_init\_\_.py                                |        0 |        0 |        0 |        0 |    100.00% |           |
| home/management/commands/\_\_init\_\_.py                       |        0 |        0 |        0 |        0 |    100.00% |           |
| home/management/commands/mock\_home\_page\_content.py          |       15 |       15 |        2 |        0 |      0.00% |      1-56 |
| home/models.py                                                 |       18 |        1 |        0 |        0 |     94.44% |        29 |
| legal/\_\_init\_\_.py                                          |        0 |        0 |        0 |        0 |    100.00% |           |
| legal/apps.py                                                  |        4 |        0 |        0 |        0 |    100.00% |           |
| legal/forms.py                                                 |        4 |        0 |        0 |        0 |    100.00% |           |
| legal/management/\_\_init\_\_.py                               |        0 |        0 |        0 |        0 |    100.00% |           |
| legal/management/commands/\_\_init\_\_.py                      |        0 |        0 |        0 |        0 |    100.00% |           |
| legal/management/commands/populate\_legal\_pages.py            |       57 |       57 |       12 |        0 |      0.00% |     1-119 |
| legal/models/\_\_init\_\_.py                                   |        6 |        0 |        0 |        0 |    100.00% |           |
| legal/models/code\_of\_conduct.py                              |       15 |        0 |        0 |        0 |    100.00% |           |
| legal/models/code\_of\_conduct\_consent.py                     |       18 |        0 |        0 |        0 |    100.00% |           |
| legal/models/cookies\_policy.py                                |       15 |        0 |        0 |        0 |    100.00% |           |
| legal/models/legal\_index.py                                   |       13 |        0 |        0 |        0 |    100.00% |           |
| legal/models/privacy\_policy.py                                |       15 |        0 |        0 |        0 |    100.00% |           |
| legal/models/terms\_of\_service.py                             |       15 |        0 |        0 |        0 |    100.00% |           |
| legal/utils.py                                                 |       21 |        2 |        6 |        2 |     85.19% |    26, 30 |
| legal/views.py                                                 |       38 |        0 |        6 |        0 |    100.00% |           |
| pedagogy/\_\_init\_\_.py                                       |        0 |        0 |        0 |        0 |    100.00% |           |
| pedagogy/apps.py                                               |        4 |        0 |        0 |        0 |    100.00% |           |
| pedagogy/management/\_\_init\_\_.py                            |        0 |        0 |        0 |        0 |    100.00% |           |
| pedagogy/management/commands/\_\_init\_\_.py                   |        0 |        0 |        0 |        0 |    100.00% |           |
| pedagogy/management/commands/create\_mock\_pedagogy\_cards.py  |       37 |       37 |       12 |        0 |      0.00% |      1-61 |
| pedagogy/models/\_\_init\_\_.py                                |        3 |        0 |        0 |        0 |    100.00% |           |
| pedagogy/models/pedagogy\_card.py                              |       34 |        2 |        4 |        0 |     94.74% |    24, 68 |
| pedagogy/models/pedagogy\_index.py                             |       39 |       12 |        2 |        0 |     65.85% |60, 63-78, 81-83 |
| pedagogy/models/pedagogy\_resource.py                          |       17 |        0 |        4 |        0 |    100.00% |           |
| publications/\_\_init\_\_.py                                   |        0 |        0 |        0 |        0 |    100.00% |           |
| publications/apps.py                                           |        4 |        0 |        0 |        0 |    100.00% |           |
| publications/management/\_\_init\_\_.py                        |        0 |        0 |        0 |        0 |    100.00% |           |
| publications/management/commands/\_\_init\_\_.py               |        0 |        0 |        0 |        0 |    100.00% |           |
| publications/management/commands/create\_mock\_publications.py |       66 |       66 |       22 |        0 |      0.00% |     1-117 |
| publications/management/commands/create\_mock\_votes.py        |       90 |       90 |       30 |        0 |      0.00% |     1-319 |
| publications/models/\_\_init\_\_.py                            |        6 |        0 |        0 |        0 |    100.00% |           |
| publications/models/event.py                                   |       34 |        2 |        0 |        0 |     94.12% |    17, 21 |
| publications/models/external\_link.py                          |       17 |        0 |        0 |        0 |    100.00% |           |
| publications/models/form.py                                    |       26 |        1 |        0 |        0 |     96.15% |        70 |
| publications/models/project.py                                 |       62 |        3 |        8 |        1 |     94.29% |38, 42, 98 |
| publications/models/publication.py                             |       88 |       51 |       36 |        0 |     31.45% |36-40, 44-49, 53-58, 62-67, 70-82, 86-91, 95-106 |
| publications/models/publication\_index.py                      |       39 |        1 |        0 |        0 |     97.44% |        26 |
| publications/services.py                                       |       64 |        1 |       14 |        1 |     97.44% |       106 |
| publications/views/\_\_init\_\_.py                             |        0 |        0 |        0 |        0 |    100.00% |           |
| publications/views/vote.py                                     |       70 |       12 |       20 |        5 |     81.11% |26-27, 46-47, 92-93, 99, 105, 117, 134-135, 141, 149->164 |
| publications/views/vote\_stats.py                              |       44 |        0 |        6 |        0 |    100.00% |           |
| publications/wagtail\_hooks.py                                 |       11 |        0 |        0 |        0 |    100.00% |           |
| search/\_\_init\_\_.py                                         |        0 |        0 |        0 |        0 |    100.00% |           |
| search/views.py                                                |       18 |       13 |        2 |        0 |     25.00% |     16-40 |
| **TOTAL**                                                      | **2271** |  **471** |  **394** |   **57** | **75.01%** |           |


## Setup coverage badge

Below are examples of the badges you can use in your main branch `README` file.

### Direct image

[![Coverage badge](https://raw.githubusercontent.com/neikow/urban-platform/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://github.com/neikow/urban-platform/blob/python-coverage-comment-action-data/htmlcov/index.html)

This is the one to use if your repository is private or if you don't want to customize anything.

### [Shields.io](https://shields.io) Json Endpoint

[![Coverage badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/neikow/urban-platform/python-coverage-comment-action-data/endpoint.json)](https://htmlpreview.github.io/?https://github.com/neikow/urban-platform/blob/python-coverage-comment-action-data/htmlcov/index.html)

Using this one will allow you to [customize](https://shields.io/endpoint) the look of your badge.
It won't work with private repositories. It won't be refreshed more than once per five minutes.

### [Shields.io](https://shields.io) Dynamic Badge

[![Coverage badge](https://img.shields.io/badge/dynamic/json?color=brightgreen&label=coverage&query=%24.message&url=https%3A%2F%2Fraw.githubusercontent.com%2Fneikow%2Furban-platform%2Fpython-coverage-comment-action-data%2Fendpoint.json)](https://htmlpreview.github.io/?https://github.com/neikow/urban-platform/blob/python-coverage-comment-action-data/htmlcov/index.html)

This one will always be the same color. It won't work for private repos. I'm not even sure why we included it.

## What is that?

This branch is part of the
[python-coverage-comment-action](https://github.com/marketplace/actions/python-coverage-comment)
GitHub Action. All the files in this branch are automatically generated and may be
overwritten at any moment.