### INIT CODE - DO NOT CHANGE ###
from pyjop import *

SimEnv.connect()
editor = LevelEditor.first()
### END INIT CODE ###

### IMPORTS - Add your imports here ###
import random

### END IMPORTS ###


class DataModel(DataModelBase):
    def __init__(self) -> None:
        super().__init__()
        self.hit_par = 0
        self.hit_pal = 0
        self.shots_fired = 0
        self.missed_shots = 0
        self.hits: Set[str] = set()
        self.mytime = 0.0
        self.last_shot_at = -1.0
        self.palindrome: list[chr] = ["&"]
        self.parasites: list[chr] = ["&"]


data = DataModel()
### END DATA MODEL ###

### CONSTRUCTION CODE ###
editor.select_map(SpawnableMaps.MilitaryBase)
editor.spawn_entity(
    SpawnableEntities.SniperRifle,
    "rifle",
    location=(4.4, -13.95, 0.8 + 1),
    rotation=(0, 0, 90),
)
editor.spawn_entity(
    SpawnableEntities.MovablePlatform,
    "platform",
    location=(4.4, -13.95, 0.83 + 1),
    rotation=(0, 0, 90),
)
editor.spawn_static_mesh(
    SpawnableMeshes.Cube,
    location=(4.4, 6.0, 0.4),
    scale=(18, 1, 2.1),
    material=SpawnableMaterials.SimpleColorWorldAligned,
    color=Colors.Slategray,
)


# Palindrome must be of minimum size 2 and maximum 10
# Parasites must be of minimum size 1 and maximum 11 - len(palindrome)
def create_palindrome() -> tuple[list[chr], list[chr]]:
    alphabet = [chr(i) for i in range(ord("a"), ord("z") + 1)]
    n = random.randint(
        1, 5
    )  # from 1 to 5 because we will duplicate in the reversed order to create the palindrome
    palindrome = random.sample(alphabet, k=n)

    for p in palindrome:
        alphabet.remove(p)

    palindrome += palindrome[::-1]
    if len(palindrome) > 2:
        if random.random() > 0.5:
            palindrome.pop(
                len(palindrome) // 2
            )  # Randomly remove a middle letter to make even and odd palindromes

    parasites = random.sample(alphabet, k=(random.randint(1, 11 - len(palindrome))))

    return palindrome, parasites


# Now i can randomly insert the parasites in the palindrome
# EXCEPTION : It is very important that a parasite never end in the middle of a palindrome !
def insert_parasites(pal: list[chr], par: list[chr]) -> list[chr]:
    len_pal = len(pal)
    spawn_list = pal[:]
    middle_letter: chr = (
        pal[len_pal // 2] if len_pal % 2 == 1 else pal[len_pal // 2 - 1]
    )  # I identify the middle letter of the palindrome so no parasite can be inserted in between

    for parasite in par:
        index = random.randint(1, len(spawn_list) - 1)

        # Ensure parasite does not end up in the middle of a palindrome
        if spawn_list[index - 1] == middle_letter:
            index += 1
        elif spawn_list[index] == middle_letter:
            index -= 1

        spawn_list = spawn_list[:index] + [parasite] + spawn_list[index:]

    return spawn_list


# Now i can attribute a color to each character
def attribute_color_to_char(spawn_list: list[chr]) -> dict[chr, Colors]:
    spawn_list_unique = list(set(spawn_list))
    colors = random.sample(list(Colors), k=len(spawn_list_unique))
    return {spawn_list_unique[i]: colors[i] for i in range(len(spawn_list_unique))}


# Now i can create the targets with rfid_tag == chr and same color for a same rfid_tag.
def spawn_targets():
    pal, par = create_palindrome()
    data.palindrome = pal
    data.parasites = par
    spawn_list = insert_parasites(pal, par)
    colors_dict = attribute_color_to_char(spawn_list)

    start_position: float = 12.4 - ((11 - len(spawn_list)) * 0.8)
    for i, char in enumerate(spawn_list):
        col = colors_dict[char]
        loc = (start_position - (i * 1.6), 6.2, 2.5)
        editor.spawn_static_mesh(
            SpawnableMeshes.Cube,
            char + str(i),
            # rfid_tag=char, # It seems that the rfid tag is not capted on collision event so i use the name instead
            location=loc,
            scale=(1, 0.5, 1),
            material=SpawnableMaterials.ColoredTexture,
            color=Colors(col),
            simulate_physics=True,
            texture=SpawnableImages.TargetIndicator,
            is_temp=True,
        )
        i += 1.6


### END CONSTRUCTION CODE ###


# Now i can put in place the logic with the rifle :
# The goal is to create the biggest palindrome possible
# If a pal is touched, the level is failed
# If all the par are touched, the level is completed


### GOAL CODE ###


def on_bullet_hit(rifle: SniperRifle, gt: float, coll: CollisionEvent):
    try:
        if coll.entity_name[0] in data.parasites:
            data.hit_par += 1
        elif coll.entity_name[0] in data.palindrome:
            data.hit_pal += 1
            data.missed_shots += 1
        else:
            data.missed_shots += 1
            return
        data.hits.add(coll.entity_name)
        editor.destroy(coll.entity_name)
        editor.show_vfx(
            SpawnableVFX.ColorBurst,
            location=editor.get_location(coll.entity_name),
            color=(
                Colors.Red if coll.entity_name[0] in data.palindrome else Colors.Green
            ),
        )
        editor.play_sound(
            SpawnableSounds.ExplosionPuff,
            location=editor.get_location(coll.entity_name),
        )
    except Exception as e:
        data.missed_shots += 1


def main_goal(goal_name: str):
    s = GoalState.Open
    txt = "Shoot the excessive targets to build the longest palindrome possible. Avoid the legitimate ones."
    if data.hit_pal > 0:
        s = GoalState.Fail
        txt = "You shot a legitimate character."

    if data.hit_par == len(data.parasites):
        s = GoalState.Success

    editor.set_goal_state(goal_name, s, txt)
    editor.set_goal_progress(
        goal_name,
        data.hit_par / len(data.parasites),
    )


editor.set_goals_intro_text("Objective:")
editor.specify_goal(
    "main_goal",
    "Build the longest palindrome possible",
    main_goal,
)


# Secondary goal : don't miss any shot
def secondary_goal(goal_name: str):
    if data.missed_shots == 0:
        s = GoalState.Open
        if data.hit_par == len(data.parasites):
            s = GoalState.Success
    elif data.missed_shots > 0:
        s = GoalState.Fail

    editor.set_goal_state(goal_name, s)


editor.specify_goal(
    "secondary_goal",
    "Perfect accuracy: Don't miss a single shot",
    secondary_goal,
    0,
    True,
    True,
)


### END GOAL CODE ###

editor.add_hint(
    0,
    ["Yo bro, how can i solve this level?"],
    """Use the riffle to get the name or color to identify the corresponding character for each targets and use these characters to build the longest palindrome possible. Then shoot the excessive characters to complete the level.
    """,
)


def on_player_command(
    gametime: float, entity_type: str, entity_name: str, command: str, val: NPArray
):
    if command == "Fire":
        data.shots_fired += 1
        data.last_shot_at = gametime


editor.on_player_command(on_player_command)


### ON BEGIN PLAY CODE - Add any code that should be executed after constructing the level once. ###
def begin_play():
    SniperRifle.first().on_bullet_hit(on_bullet_hit)
    on_reset()


editor.on_begin_play(begin_play)
### END ON BEGIN PLAY CODE ###


### ON LEVEL RESET CODE - Add code that should be executed on every level reset. ###
def on_reset():
    MovablePlatform.first().attach_entities()
    MovablePlatform.first().editor_set_location_limits((0, 12, 3))
    data.reset()
    spawn_targets()


editor.on_level_reset(on_reset)
### END ON LEVEL RESET CODE ###


### LEVEL TICK CODE - Add code that should be executed on every simulation tick. ###


# def on_tick(simtime: float, deltatime: float):
#     if data.mytime > 9:
#         data.mytime = 0.0
#         spawn_target()
#     else:
#         data.mytime += deltatime


# editor.on_tick(on_tick)
### END LEVEL TICK CODE ###


### EOF CODE - DO NOT CHANGE ###
editor.run_editor_level()
### EOF ###
