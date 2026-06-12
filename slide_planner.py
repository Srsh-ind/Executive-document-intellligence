from slide_agent import recommend_slide_plan


def split_items(items, max_items=6):
    """
    Splits long lists into smaller chunks for readable slides.
    """
    return [
        items[i:i + max_items]
        for i in range(0, len(items), max_items)
    ]


def build_slide_plan(analysis):
    """
    Builds final slide plan with overflow handling.
    """
    base_plan = recommend_slide_plan(analysis)
    final_plan = []

    for slide in base_plan:
        slide_type = slide.get("type")

        if slide_type == "bullets":
            source = slide.get("source", "")
            items = analysis.get(source, [])

            chunks = split_items(items)

            for index, chunk in enumerate(chunks):
                new_slide = slide.copy()
                new_slide["items"] = chunk

                if index > 0:
                    new_slide["title"] = f"{slide.get('title')} continued"

                final_plan.append(new_slide)

        elif slide_type == "custom_section":
            items = slide.get("items", [])
            chunks = split_items(items)

            for index, chunk in enumerate(chunks):
                new_slide = slide.copy()
                new_slide["items"] = chunk

                if index > 0:
                    new_slide["title"] = f"{slide.get('title')} continued"

                final_plan.append(new_slide)

        else:
            final_plan.append(slide)

    return final_plan