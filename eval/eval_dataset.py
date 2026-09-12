# eval/eval_dataset.py

FALLBACK = "I could not find a reliable answer to that in the provided documents."

EVAL_QUESTIONS = [
    {
        "question": "Who are the authors of the green flashes paper?",
        "ground_truth": "The authors are Gilbert Green and Naomi Watanabe."
    },
    {
        "question": "What institution are the authors affiliated with?",
        "ground_truth": "The authors are affiliated with Florida Gulf Coast University and the Space Telescope Science Institute."
    },
    {
        "question": "What is the main topic of the paper?",
        "ground_truth": "The paper studies green flashes observed in optical and infrared during an extreme electric storm."
    },
    {
        "question": "What causes the green and blue colors in lightning flashes?",
        "ground_truth": "The colors are caused by interactions of the discharge with oxygen atoms, which emit blue to emerald-green light."
    },
    {
        "question": "What date was the storm observed?",
        "ground_truth": "The storm was observed on 17 April 2023."
    },
    {
        "question": "What is the role of atmospheric concentration in the observed coloration?",
        "ground_truth": "Atmospheric concentration is the most significant contributor to the visual coloration observed in the green flashes."
    },
    {
        "question": "What instruments were used in the study?",
        "ground_truth": "The study used optical and infrared observation equipment including GLM data for lightning location mapping."
    },
    {
        "question": "What is GLM data?",
        "ground_truth": "GLM refers to Geostationary Lightning Mapper data used to track lightning flash locations."
    },
    {
        "question": "What causes pinkish and violet colors in lightning?",
        "ground_truth": "Pinkish and violet colors are caused by collisions with nitrogen molecules and ions."
    },
    {
        "question": "Where was the study conducted?",
        "ground_truth": "The study was conducted in Florida, with coordinates around 25.95N to 26.35N and 81.5W to 82.0W."
    },
    {
        "question": "What journal was this paper published in?",
        "ground_truth": "The paper was published in Applied Sciences (Appl. Sci.) in 2024."
    },
    {
        "question": "What is the significance of oceanic flashes in the study?",
        "ground_truth": "Oceanic flashes have higher optical power and energy, and may transmit green-blue light through clean air above the ocean."
    },
    {
        "question": "What is the capital of France?",
        "ground_truth": FALLBACK
    },
    {
        "question": "Who won the FIFA World Cup in 2022?",
        "ground_truth": FALLBACK
    },
    {
        "question": "What is the boiling point of water?",
        "ground_truth": FALLBACK
    },
]