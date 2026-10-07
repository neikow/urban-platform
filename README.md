# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/neikow/urban-platform/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                           |    Stmts |     Miss |   Branch |   BrPart |      Cover |   Missing |
|--------------------------------------------------------------- | -------: | -------: | -------: | -------: | ---------: | --------: |
| about/\_\_init\_\_.py                                          |        0 |        0 |        0 |        0 |    100.00% |           |
| about/apps.py                                                  |        4 |        0 |        0 |        0 |    100.00% |           |
| about/blocks.py                                                |       53 |        0 |        0 |        0 |    100.00% |           |
| about/management/\_\_init\_\_.py                               |        0 |        0 |        0 |        0 |    100.00% |           |
| about/management/commands/\_\_init\_\_.py                      |        0 |        0 |        0 |        0 |    100.00% |           |
| about/management/commands/populate\_about\_pages.py            |       19 |       19 |        6 |        0 |      0.00% |      1-32 |
| about/models/\_\_init\_\_.py                                   |        5 |        0 |        0 |        0 |    100.00% |           |
| about/models/about\_commission.py                              |       17 |        0 |        0 |        0 |    100.00% |           |
| about/models/about\_dev\_team.py                               |       17 |        0 |        0 |        0 |    100.00% |           |
| about/models/about\_index.py                                   |       14 |        0 |        0 |        0 |    100.00% |           |
| about/models/about\_website.py                                 |       16 |        0 |        0 |        0 |    100.00% |           |
| about/page\_templates.py                                       |       15 |        0 |        0 |        0 |    100.00% |           |
| core/\_\_init\_\_.py                                           |        0 |        0 |        0 |        0 |    100.00% |           |
| core/admin\_dashboard.py                                       |       75 |        0 |        6 |        1 |     98.77% |   68-\>76 |
| core/admin\_menu.py                                            |       51 |        2 |        8 |        2 |     93.22% |   72, 111 |
| core/apps.py                                                   |       15 |        0 |        0 |        0 |    100.00% |           |
| core/auth\_backends.py                                         |       18 |        2 |        4 |        2 |     81.82% |    69, 72 |
| core/blocks.py                                                 |      182 |        0 |        4 |        2 |     98.92% |255-\>265, 262-\>265 |
| core/cache.py                                                  |       16 |        2 |        2 |        1 |     83.33% |33-34, 40-\>exit |
| core/context\_processors.py                                    |        6 |        0 |        0 |        0 |    100.00% |           |
| core/data\_export.py                                           |       36 |        0 |        2 |        0 |    100.00% |           |
| core/emails/\_\_init\_\_.py                                    |        0 |        0 |        0 |        0 |    100.00% |           |
| core/emails/services.py                                        |       50 |        3 |        4 |        1 |     92.59% |27, 79, 118 |
| core/emails/tasks.py                                           |       66 |       10 |        4 |        0 |     85.71% |44-48, 81-85 |
| core/emails/tokens.py                                          |       46 |        3 |        6 |        1 |     92.31% | 58, 61-62 |
| core/management/\_\_init\_\_.py                                |        0 |        0 |        0 |        0 |    100.00% |           |
| core/management/commands/\_content\_transfer.py                |       51 |        3 |       22 |        3 |     91.78% |105, 126, 134 |
| core/management/commands/export\_content.py                    |      104 |       12 |       28 |        7 |     85.61% |67-\>65, 73-\>71, 94-95, 152-\>144, 161-162, 166-167, 185-186, 190-191, 212-213 |
| core/management/commands/import\_content.py                    |      154 |       18 |       46 |        8 |     85.00% |59-60, 66, 105-108, 126, 140-142, 152-153, 188-189, 199, 208, 211 |
| core/models/\_\_init\_\_.py                                    |        8 |        0 |        0 |        0 |    100.00% |           |
| core/models/announcement.py                                    |       26 |        0 |        0 |        0 |    100.00% |           |
| core/models/city.py                                            |        5 |        1 |        0 |        0 |     80.00% |         8 |
| core/models/city\_district.py                                  |       10 |        0 |        0 |        0 |    100.00% |           |
| core/models/city\_neighborhood.py                              |       15 |        2 |        0 |        0 |     86.67% |    18, 22 |
| core/models/email\_event.py                                    |       30 |        0 |        0 |        0 |    100.00% |           |
| core/models/neighborhood\_association.py                       |       13 |        1 |        0 |        0 |     92.31% |        26 |
| core/models/notification\_dispatch.py                          |       16 |        1 |        0 |        0 |     93.75% |        27 |
| core/models/user.py                                            |       96 |        4 |        8 |        2 |     94.23% |35, 50, 144, 169 |
| core/notifications/\_\_init\_\_.py                             |       16 |        0 |        0 |        0 |    100.00% |           |
| core/notifications/recipients.py                               |        6 |        0 |        0 |        0 |    100.00% |           |
| core/notifications/tasks.py                                    |       40 |        6 |        6 |        1 |     84.78% | 71-75, 80 |
| core/notifications/tokens.py                                   |       11 |        0 |        0 |        0 |    100.00% |           |
| core/page\_templates.py                                        |       48 |        0 |       10 |        0 |    100.00% |           |
| core/permissions.py                                            |       19 |        0 |       10 |        0 |    100.00% |           |
| core/sitemaps.py                                               |       72 |       21 |        6 |        0 |     65.38% |31-33, 36, 39, 47, 55-65, 73, 81, 89, 97, 105, 113-122 |
| core/templatetags/\_\_init\_\_.py                              |        0 |        0 |        0 |        0 |    100.00% |           |
| core/templatetags/announcement\_tags.py                        |       16 |        0 |        6 |        0 |    100.00% |           |
| core/templatetags/custom\_blocks.py                            |       18 |        7 |        8 |        3 |     53.85% |11, 13, 16-19, 24-39 |
| core/templatetags/django\_settings.py                          |        6 |        0 |        0 |        0 |    100.00% |           |
| core/templatetags/forms.py                                     |        6 |        0 |        0 |        0 |    100.00% |           |
| core/templatetags/navigation\_tags.py                          |       53 |        3 |       18 |        4 |     90.14% |22-\>25, 36, 48, 53 |
| core/templatetags/social\_meta.py                              |       28 |        0 |        8 |        1 |     97.22% |   50-\>52 |
| core/templatetags/structured\_data.py                          |      113 |        4 |       42 |       10 |     90.97% |30-31, 90-\>93, 100, 133-\>138, 135-\>138, 154-\>157, 162-\>165, 166-\>169, 173-\>189, 181-\>187, 200 |
| core/toc.py                                                    |       41 |        1 |       22 |        1 |     96.83% |        52 |
| core/utils.py                                                  |        6 |        0 |        2 |        0 |    100.00% |           |
| core/views/\_\_init\_\_.py                                     |        0 |        0 |        0 |        0 |    100.00% |           |
| core/views/account\_delete.py                                  |       39 |        1 |        4 |        1 |     95.35% |        38 |
| core/views/auth\_mixins.py                                     |       32 |        0 |       10 |        0 |    100.00% |           |
| core/views/data\_export.py                                     |       26 |        0 |        2 |        0 |    100.00% |           |
| core/views/docs.py                                             |       33 |       20 |       10 |        0 |     30.23% |16-17, 20-23, 26-46 |
| core/views/email\_verify.py                                    |       44 |        0 |       10 |        0 |    100.00% |           |
| core/views/health.py                                           |        8 |        0 |        0 |        0 |    100.00% |           |
| core/views/login.py                                            |       39 |        0 |       12 |        0 |    100.00% |           |
| core/views/logout.py                                           |        8 |        0 |        0 |        0 |    100.00% |           |
| core/views/me.py                                               |       16 |        0 |        0 |        0 |    100.00% |           |
| core/views/notifications.py                                    |       32 |        1 |        6 |        1 |     94.74% |        35 |
| core/views/page\_templates.py                                  |       39 |        0 |        6 |        0 |    100.00% |           |
| core/views/password\_reset.py                                  |       79 |        4 |       12 |        3 |     92.31% |77, 90, 113-114, 119-\>124 |
| core/views/profile\_edit.py                                    |      126 |        6 |       26 |        6 |     92.11% |86, 96, 100, 129, 139, 146 |
| core/views/register.py                                         |       90 |        7 |       22 |        8 |     86.61% |68, 81, 87, 94, 96, 98, 136-\>140, 163 |
| core/wagtail\_forms.py                                         |       35 |        2 |        6 |        2 |     90.24% |    33, 53 |
| core/wagtail\_hooks.py                                         |       71 |        0 |        8 |        1 |     98.73% | 88-\>exit |
| core/wagtail\_viewsets.py                                      |       19 |        3 |        0 |        0 |     84.21% |     22-24 |
| core/widgets.py                                                |       45 |       19 |       16 |        3 |     47.54% |16, 28-35, 49, 68-71, 81-88, 98 |
| home/\_\_init\_\_.py                                           |        0 |        0 |        0 |        0 |    100.00% |           |
| home/apps.py                                                   |        4 |        0 |        0 |        0 |    100.00% |           |
| home/blocks.py                                                 |      224 |        7 |       20 |        4 |     95.49% |119, 131, 133, 285, 405-407 |
| home/management/\_\_init\_\_.py                                |        0 |        0 |        0 |        0 |    100.00% |           |
| home/management/commands/\_\_init\_\_.py                       |        0 |        0 |        0 |        0 |    100.00% |           |
| home/management/commands/mock\_home\_page\_content.py          |       15 |       15 |        2 |        0 |      0.00% |      1-56 |
| home/models.py                                                 |       19 |        1 |        0 |        0 |     94.74% |        35 |
| home/page\_templates.py                                        |       17 |        0 |        0 |        0 |    100.00% |           |
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
| legal/utils.py                                                 |       25 |        2 |        8 |        2 |     87.88% |    36, 40 |
| legal/views.py                                                 |       38 |        0 |        6 |        0 |    100.00% |           |
| pedagogy/\_\_init\_\_.py                                       |        0 |        0 |        0 |        0 |    100.00% |           |
| pedagogy/apps.py                                               |        4 |        0 |        0 |        0 |    100.00% |           |
| pedagogy/blocks.py                                             |       12 |        0 |        0 |        0 |    100.00% |           |
| pedagogy/management/\_\_init\_\_.py                            |        0 |        0 |        0 |        0 |    100.00% |           |
| pedagogy/management/commands/\_\_init\_\_.py                   |        0 |        0 |        0 |        0 |    100.00% |           |
| pedagogy/management/commands/create\_mock\_pedagogy\_cards.py  |       37 |       37 |       12 |        0 |      0.00% |      1-61 |
| pedagogy/models/\_\_init\_\_.py                                |        3 |        0 |        0 |        0 |    100.00% |           |
| pedagogy/models/pedagogy\_card.py                              |       35 |        2 |        4 |        0 |     94.87% |    26, 70 |
| pedagogy/models/pedagogy\_index.py                             |       50 |        5 |        2 |        1 |     88.46% |70, 79, 99-105 |
| pedagogy/models/pedagogy\_resource.py                          |       18 |        0 |        4 |        0 |    100.00% |           |
| pedagogy/page\_templates.py                                    |       13 |        0 |        0 |        0 |    100.00% |           |
| publications/\_\_init\_\_.py                                   |        0 |        0 |        0 |        0 |    100.00% |           |
| publications/apps.py                                           |        6 |        0 |        0 |        0 |    100.00% |           |
| publications/blocks.py                                         |       12 |        0 |        0 |        0 |    100.00% |           |
| publications/event\_reminders.py                               |       21 |        0 |        2 |        0 |    100.00% |           |
| publications/geo.py                                            |       34 |        0 |        8 |        0 |    100.00% |           |
| publications/ical.py                                           |       47 |        1 |       14 |        3 |     93.44% |55, 64-\>66, 71-\>73 |
| publications/management/\_\_init\_\_.py                        |        0 |        0 |        0 |        0 |    100.00% |           |
| publications/management/commands/\_\_init\_\_.py               |        0 |        0 |        0 |        0 |    100.00% |           |
| publications/management/commands/build\_map\_tiles.py          |       43 |       43 |        4 |        0 |      0.00% |     11-95 |
| publications/management/commands/create\_mock\_publications.py |       66 |       66 |       22 |        0 |      0.00% |     1-119 |
| publications/management/commands/create\_mock\_votes.py        |       91 |       91 |       30 |        0 |      0.00% |     1-323 |
| publications/management/commands/runserver.py                  |       40 |        9 |       10 |        1 |     72.00% |28, 49-52, 57-60 |
| publications/models/\_\_init\_\_.py                            |       10 |        0 |        0 |        0 |    100.00% |           |
| publications/models/event.py                                   |       49 |        0 |        4 |        1 |     98.11% | 106-\>109 |
| publications/models/event\_interest.py                         |       13 |        1 |        0 |        0 |     92.31% |        35 |
| publications/models/external\_link.py                          |       17 |        0 |        0 |        0 |    100.00% |           |
| publications/models/form.py                                    |       27 |        1 |        0 |        0 |     96.30% |        73 |
| publications/models/idea.py                                    |       17 |        1 |        0 |        0 |     94.12% |        54 |
| publications/models/poll\_closure.py                           |       16 |        1 |        0 |        0 |     93.75% |        40 |
| publications/models/project.py                                 |       90 |        0 |       12 |        0 |    100.00% |           |
| publications/models/project\_update.py                         |       18 |        1 |        0 |        0 |     94.44% |        47 |
| publications/models/publication.py                             |       20 |        0 |        0 |        0 |    100.00% |           |
| publications/models/publication\_index.py                      |       58 |        1 |        0 |        0 |     98.28% |        47 |
| publications/page\_templates.py                                |       22 |        0 |        0 |        0 |    100.00% |           |
| publications/polls.py                                          |       28 |        0 |        4 |        0 |    100.00% |           |
| publications/project\_updates.py                               |       25 |        1 |        6 |        1 |     93.55% |        38 |
| publications/services.py                                       |       83 |        0 |       18 |        0 |    100.00% |           |
| publications/signals.py                                        |        7 |        0 |        0 |        0 |    100.00% |           |
| publications/tasks.py                                          |       21 |        4 |        0 |        0 |     80.95% |8-10, 32-34 |
| publications/views/\_\_init\_\_.py                             |        0 |        0 |        0 |        0 |    100.00% |           |
| publications/views/event\_interest.py                          |       34 |        2 |        8 |        2 |     90.48% |    39, 54 |
| publications/views/feeds.py                                    |       49 |        0 |        2 |        0 |    100.00% |           |
| publications/views/idea.py                                     |       56 |        6 |       20 |        5 |     85.53% |27-28, 73, 76, 88, 109, 120-\>131 |
| publications/views/idea\_stats.py                              |       41 |        0 |        2 |        0 |    100.00% |           |
| publications/views/mixins.py                                   |       37 |        0 |       14 |        0 |    100.00% |           |
| publications/views/poll\_close.py                              |       26 |        2 |        4 |        2 |     86.67% |    24, 41 |
| publications/views/vote.py                                     |       66 |        7 |       26 |        6 |     85.87% |34-35, 87, 90, 96, 108, 130, 138-\>153 |
| publications/views/vote\_stats.py                              |       60 |        0 |        8 |        0 |    100.00% |           |
| publications/wagtail\_hooks.py                                 |       22 |        0 |        2 |        1 |     95.83% | 47-\>exit |
| publications/widgets.py                                        |       20 |        0 |        2 |        0 |    100.00% |           |
| **TOTAL**                                                      | **4497** |  **552** |  **730** |  **104** | **85.08%** |           |


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