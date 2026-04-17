# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/neikow/urban-platform/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                           |    Stmts |     Miss |   Branch |   BrPart |      Cover |   Missing |
|--------------------------------------------------------------- | -------: | -------: | -------: | -------: | ---------: | --------: |
| about/\_\_init\_\_.py                                          |        0 |        0 |        0 |        0 |    100.00% |           |
| about/apps.py                                                  |        4 |        0 |        0 |        0 |    100.00% |           |
| about/blocks.py                                                |       40 |        0 |        0 |        0 |    100.00% |           |
| about/management/\_\_init\_\_.py                               |        0 |        0 |        0 |        0 |    100.00% |           |
| about/management/commands/\_\_init\_\_.py                      |        0 |        0 |        0 |        0 |    100.00% |           |
| about/management/commands/populate\_about\_pages.py            |       19 |       19 |        6 |        0 |      0.00% |      1-32 |
| about/models/\_\_init\_\_.py                                   |        5 |        0 |        0 |        0 |    100.00% |           |
| about/models/about\_commission.py                              |       16 |        0 |        0 |        0 |    100.00% |           |
| about/models/about\_dev\_team.py                               |       16 |        0 |        0 |        0 |    100.00% |           |
| about/models/about\_index.py                                   |       14 |        0 |        0 |        0 |    100.00% |           |
| about/models/about\_website.py                                 |       14 |        0 |        0 |        0 |    100.00% |           |
| core/\_\_init\_\_.py                                           |        0 |        0 |        0 |        0 |    100.00% |           |
| core/apps.py                                                   |        6 |        0 |        0 |        0 |    100.00% |           |
| core/blocks.py                                                 |      170 |        4 |        0 |        0 |     97.65% |   240-250 |
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
| core/models/user.py                                            |       79 |        4 |        6 |        3 |     91.76% |34, 50, 52, 132 |
| core/signals.py                                                |       20 |        0 |       10 |        1 |     96.67% | 34-\>exit |
| core/sitemaps.py                                               |       72 |       21 |        6 |        0 |     65.38% |31-33, 36, 39, 47, 55-65, 73, 81, 89, 97, 105, 113-122 |
| core/templatetags/\_\_init\_\_.py                              |        0 |        0 |        0 |        0 |    100.00% |           |
| core/templatetags/custom\_blocks.py                            |       18 |       11 |        8 |        0 |     26.92% |10-19, 24-39 |
| core/templatetags/django\_settings.py                          |        6 |        0 |        0 |        0 |    100.00% |           |
| core/templatetags/forms.py                                     |        6 |        0 |        0 |        0 |    100.00% |           |
| core/templatetags/navigation\_tags.py                          |       53 |        3 |       18 |        4 |     90.14% |22-\>25, 36, 48, 53 |
| core/templatetags/structured\_data.py                          |      112 |        6 |       42 |       15 |     86.36% |30-31, 90-\>93, 100, 125-\>128, 129-\>132, 133-\>138, 135-\>138, 139, 141, 154-\>157, 158-\>161, 162-\>165, 166-\>169, 173-\>189, 181-\>187, 200 |
| core/toc.py                                                    |       41 |        1 |       22 |        1 |     96.83% |        52 |
| core/utils.py                                                  |        6 |        0 |        2 |        0 |    100.00% |           |
| core/views/\_\_init\_\_.py                                     |        0 |        0 |        0 |        0 |    100.00% |           |
| core/views/account\_delete.py                                  |       39 |        1 |        4 |        1 |     95.35% |        38 |
| core/views/auth\_mixins.py                                     |       29 |        0 |       10 |        0 |    100.00% |           |
| core/views/docs.py                                             |       26 |       16 |        8 |        0 |     29.41% | 13, 18-38 |
| core/views/email\_verify.py                                    |       24 |        0 |        4 |        0 |    100.00% |           |
| core/views/login.py                                            |       34 |        1 |       10 |        1 |     95.45% |        57 |
| core/views/logout.py                                           |        8 |        0 |        0 |        0 |    100.00% |           |
| core/views/me.py                                               |        9 |        0 |        0 |        0 |    100.00% |           |
| core/views/password\_reset.py                                  |       70 |        4 |       10 |        3 |     91.25% |67, 80, 103-104, 109-\>114 |
| core/views/profile\_edit.py                                    |      119 |        6 |       24 |        6 |     91.61% |62, 72, 76, 105, 115, 122 |
| core/views/register.py                                         |       78 |       10 |       18 |        7 |     82.29% |66, 79, 85, 92, 94, 96, 107-109, 151 |
| core/wagtail\_hooks.py                                         |       99 |        8 |       18 |        9 |     85.47% |60-\>76, 124, 159, 161, 163, 165, 205, 207, 209 |
| core/widgets.py                                                |       45 |       19 |       16 |        3 |     47.54% |16, 28-35, 49, 68-71, 81-88, 98 |
| home/\_\_init\_\_.py                                           |        0 |        0 |        0 |        0 |    100.00% |           |
| home/apps.py                                                   |        4 |        0 |        0 |        0 |    100.00% |           |
| home/management/\_\_init\_\_.py                                |        0 |        0 |        0 |        0 |    100.00% |           |
| home/management/commands/\_\_init\_\_.py                       |        0 |        0 |        0 |        0 |    100.00% |           |
| home/management/commands/mock\_home\_page\_content.py          |       15 |       15 |        2 |        0 |      0.00% |      1-56 |
| home/models.py                                                 |       18 |        1 |        0 |        0 |     94.44% |        33 |
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
| publications/models/event.py                                   |       44 |        2 |        4 |        1 |     93.75% |19, 23, 97-\>100 |
| publications/models/external\_link.py                          |       17 |        0 |        0 |        0 |    100.00% |           |
| publications/models/form.py                                    |       26 |        1 |        0 |        0 |     96.15% |        70 |
| publications/models/project.py                                 |       62 |        3 |        8 |        1 |     94.29% |38, 42, 98 |
| publications/models/publication.py                             |      115 |       72 |       50 |        0 |     27.27% |38-42, 46-51, 55-60, 64-69, 72-84, 88-93, 97-103, 107-127, 131-138 |
| publications/models/publication\_index.py                      |       46 |        1 |        0 |        0 |     97.83% |        35 |
| publications/services.py                                       |       77 |        1 |       18 |        1 |     97.89% |       137 |
| publications/views/\_\_init\_\_.py                             |        0 |        0 |        0 |        0 |    100.00% |           |
| publications/views/vote.py                                     |       70 |       12 |       20 |        5 |     81.11% |26-27, 46-47, 92-93, 99, 105, 117, 134-135, 141, 149-\>164 |
| publications/views/vote\_stats.py                              |       59 |        0 |        8 |        0 |    100.00% |           |
| publications/wagtail\_hooks.py                                 |       11 |        0 |        0 |        0 |    100.00% |           |
| search/\_\_init\_\_.py                                         |        0 |        0 |        0 |        0 |    100.00% |           |
| search/views.py                                                |       18 |       13 |        2 |        0 |     25.00% |     16-40 |
| **TOTAL**                                                      | **2623** |  **537** |  **458** |   **64** | **75.04%** |           |


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