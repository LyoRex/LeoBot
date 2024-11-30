import discord
from discord.ext import commands, tasks
import random
import json

# Offense Shoot (0) & Defense Blocks (0) --> Defense Turn
# Offense Shoot (0) & Defense Steals (1) --> Offense gets +2
# Offense Cross (1) & Defense Blocks (0) --> Offense gets to paint
#     Offense Shoot (0) & Defense Blocks (0) --> Defense Turn
#     Offense Shoot (0) & Defence Steals (1) --> Offense gets +1 and keep possession (fouled)
#     Offense Pump Fake (1) & Defense Blocks (0) --> Offense gets +1 and keep possession (fouled)
#     Offense Pump Fake (1) & Defense Steals (1) --> Defense Turn
# Offense Cross (1) & Defense Steals (1) --> Defense Turn

# Shoot 0, Cross/Pump-fake 1
# Block 0, Steal 1

class Baller(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot
        self.accept_timeout_length = 10
        self.game_timeout_length = 30

        self.bot = bot
        self.guild_games = {}

        self.THREE_POINT_WEIGHT = 3
        self.TWO_POINT_WEIGHT = 2

        self.DEFAULT_BALLER_DATA = {"games_played": 0, "wins": 0, "losses": 0, "forfeits": 0, 
                                    "points": 0, "3pas": 0, "3pms": 0, "fgas": 0, "fgms": 0, 
                                    "and1s": 0, "dunks": 0, "layups": 0, "blocks": 0, "steals": 0, 
                                    "tos": 0, "fouls": 0}

        # GAMEPLAY STRINGS
        ### STAGE 1
        # OFFENSE 0 & DEFENSE 0 : NEXT TURN (Switch) ; Blocked
        # OFFENSE 0 & DEFENSE 1 : NEXT TURN (Switch) ; Offense +3 pts
        # OFFENSE 1 & DEFENSE 0 : NEXT STAGE (Stage 2) ; Offense gets into paint
        # OFFENSE 1 & DEFENSE 1 : NEXT TURN (Switch) ; Stolen
        self.STAGE_1_OFFENSE_0_DEFENSE_0 = ["**{0}'s shot was sent flying by {1}!**",
                                            "**{1} blocks {0}'s 3 pointer out of bounds!**",
                                            "**DENIED! {0} gets their shot blocked!**"
        ]

        self.STAGE_1_OFFENSE_0_DEFENSE_1 = ["**{0} drains the 3 pointer!**",
                                            "**{0} hits the tough 3 with {1}'s hand right in their face!**",
                                            "**{0} steps back and swishes the 3 pointer!**"
        ]

        self.STAGE_1_OFFENSE_1_DEFENSE_0 = ["**{0} goes behind the back to drive into the paint.**",
                                            "**{0} spins away from {1} to get into the paint!**",
                                            "**Insane dribble moves! {0} works their way to the basket!**",
                                            "**{0}'s freezes {1} with a pump fake and works their way into the paint!**"
        ]

        self.STAGE_1_OFFENSE_1_DEFENSE_1 = ["**{1} reads {0}'s crossover beautifully and strips the ball away!**",
                                            "**{1} pokes the ball free, and {0} turns it over.**",
                                            "**{0}'s loose handling leads to a steal by {1}!**"
        ]
        ### STAGE 2
        # OFFENSE 0 & DEFENSE 0 : NEXT TURN (Switch) ; Blocked
        # OFFENSE 0 & DEFENSE 1 : NEXT TURN (Stay) ; Offense +2 pts (dunk)
        # OFFENSE 1 & DEFENSE 0 : NEXT STAGE (Stay) ; Offense +2 pts (cross over layup/floater)
        # OFFENSE 1 & DEFENSE 1 : NEXT TURN (Switch) ; Stolen
        self.STAGE_2_OFFENSE_0_DEFENSE_0 = ["**{0} goes for the dunk but is met at the rim by {1}!**",
                                            "**{1} swats {0}'s layup off the backboard!**",
                                            "**BLOCKED BY {1}! {0}'s layup was sent away!**"
        ]
        self.STAGE_2_OFFENSE_0_DEFENSE_1 = ["**SLAM DUNK!! {0} yams it all over {1} and gets the foul!**",
                                            "**AND 1! {0} with the reverse jam while getting fouled by {1}!**",
                                            "**IF YOU DON'T LIKE THAT, YOU DON'T LIKE STREETBALL! {0} gets the dunk AND one!!**"
        ]
        self.STAGE_2_OFFENSE_1_DEFENSE_0 = ["**{0}'s pump fake gets {1} in the air. {0} hits the tough double clutch with the foul!**",
                                            "**{0} goes up and under and gets hit while draining the reverse layup!**",
                                            "**DID SOMEONE BRING THE POPCORN MACHINE? {0} has {1} jumping! Count the bucket AND one!**"
        ]
        self.STAGE_2_OFFENSE_1_DEFENSE_1 = ["**{0}'s pump fake was read beautifully by {1}, leading to a turnover!**",
                                            "**{1} didn't bite on {0}'s pump fake, and the ball was stolen!**",
                                            "**COOKIES! {0} gets the ball stolen right out of their hands!**"
        ]

        self.game_loop.start()

    @commands.command(aliases=["bstart"], help="Start a baller game", usage="&ballerstart")
    @commands.guild_only()
    async def ballerstart(self, ctx, *args):
        member = ctx.author
        guild = ctx.guild
        channel = ctx.channel

        # Cannot start a baller game if another is already in progress within the server
        if guild.id in self.guild_games:
            await ctx.send(f"A Baller game has already been started in {guild.name}")
            return
        # Must pass in one or two arguments.
        # First argument is the player to challenge (mandatory)
        # Second argument is the target score (leave blank and default will be set to 21)
        if len(args) != 1 and len(args) != 2:
            await ctx.send("You must challenge another member of the server!")
            return
        # Loop through all members of the server
        member_ids = []
        for m in guild.members:
            member_ids.append(m.id)
        target_id = int(args[0].replace("<@","").replace(">",""))
        target_member = None
        # Return if can't find @ed member in server
        if target_id in member_ids:
            target_member = guild.get_member(target_id)
        if target_member == None:
            return
        # Loop through all guilds with active games (all keys in self.guild_games) and check if there you or your challengee are already in a game in another server
        for g in self.guild_games:
            if self.guild_games[g]["player1"].id == member.id or self.guild_games[g]["player2"].id == member.id:
                await ctx.send(f"You are already playing a Baller 1v1 in another server!")
                return
            if self.guild_games[g]["player1"].id == target_id or self.guild_games[g]["player2"].id == target_id:
                await ctx.send(f"{target_member.display_name} is already playing a Baller 1v1 in another server!")
                return
        if target_member == member:
            await ctx.send(f"You cannot challenge yourself to a Baller 1v1!")
            return
        if target_member.bot:
            await ctx.send(f"You cannot challenge a Bot to a Baller 1v1!")
            return
        
        if len(args) == 2:
            try:
                target_score = int(args[1])
                if target_score < 5 or target_score > 21:
                    raise ValueError
            except ValueError:
                await ctx.send("The target score must be a number between 5 and 21.\nThe target score will default to 21...")
                target_score = 21
        else:
            target_score = 21

        await ctx.send(f"**{target_member.mention}**, you have been challenged by **{member.mention}** to a Baller 1v1.\nThe target score is **{target_score}**.\n Type 'a' to accept or 'd' to decline.")
        self.reset_game(guild.id, guild, channel, member, target_member, target_score)

    @commands.command(aliases=["bstats"], help="Show your Baller 1v1 stats in this server", usage="&ballerstats")
    @commands.guild_only()
    async def ballerstats(self, ctx, *args):
        member = ctx.author
        guild = ctx.guild
        channel = ctx.channel

        target_member_id = str(member.id)
        target_member = member
        if len(args) == 1:
            arg_id = int(args[0].replace("<@","").replace(">",""))
            all_guild_member_ids = [m.id for m in guild.members]
            if arg_id in all_guild_member_ids:
                target_member_id = str(arg_id)
                target_member = guild.get_member(arg_id)

        with open(self.bot.data_file, 'r') as f:
            all_guilds_data_dict = json.load(f)
            guild_data = all_guilds_data_dict[str(guild.id)]['baller_data']
            out_string = ""
            found_member = False
            for member_id in guild_data:
                if member_id == target_member_id:
                    member_data_dict = guild_data[member_id]

                    out_string += "**__GAMES__**\n"
                    out_string += f"Games Played: {member_data_dict['games_played']}\n"
                    out_string += f"Games Won: {member_data_dict['wins']}\n"
                    out_string += f"Games Lost: {member_data_dict['losses']}\n"
                    out_string += f"Games Forfeited: {member_data_dict['forfeits']}\n"
                    out_string += "\n**__AVERAGES__**\n"
                    out_string += f"Points per Game: {member_data_dict['points'] / member_data_dict['games_played']}\n"
                    if member_data_dict['fgas'] == 0:
                        out_string += "FG%: N/A\n"
                    else:
                        out_string += f"FG%: {member_data_dict['fgms'] / member_data_dict['fgas']}\n"
                    if member_data_dict['3pas'] == 0:
                        out_string += "3P%: N/A\n"
                    else:
                        out_string += f"3P%: {member_data_dict['3pms'] / member_data_dict['3pas']}\n"
                    out_string += f"3PA per Game: {member_data_dict['3pas'] / member_data_dict['games_played']}\n"
                    out_string += f"3PM per Game: {member_data_dict['3pms'] / member_data_dict['games_played']}\n"
                    out_string += f"And1s per Game: {member_data_dict['and1s'] / member_data_dict['games_played']}\n"
                    out_string += f"Dunks per Game: {member_data_dict['dunks'] / member_data_dict['games_played']}\n"
                    out_string += f"Layups per Game: {member_data_dict['layups'] / member_data_dict['games_played']}\n"
                    out_string += f"Blocks per Game: {member_data_dict['blocks'] / member_data_dict['games_played']}\n"
                    out_string += f"Steals per Game: {member_data_dict['steals'] / member_data_dict['games_played']}\n"
                    out_string += f"Turnovers per Game: {member_data_dict['tos'] / member_data_dict['games_played']}\n"
                    out_string += f"Fouls per Game: {member_data_dict['fouls'] / member_data_dict['games_played']}\n"
                    out_string += "\n**__TOTALS__**\n"
                    out_string += f"Total Points: {member_data_dict['points']}\n"
                    out_string += f"Total FGM: {member_data_dict['fgms']}\n"
                    out_string += f"Total FGA: {member_data_dict['fgas']}\n"
                    out_string += f"Total 3PA: {member_data_dict['3pas']}\n"
                    out_string += f"Total 3PM: {member_data_dict['3pms']}\n"
                    out_string += f"Total And1s: {member_data_dict['and1s']}\n"
                    out_string += f"Total Dunks: {member_data_dict['dunks']}\n"
                    out_string += f"Total Layups: {member_data_dict['layups']}\n"
                    out_string += f"Total Blocks: {member_data_dict['blocks']}\n"
                    out_string += f"Total Steals: {member_data_dict['steals']}\n"
                    out_string += f"Total TOs: {member_data_dict['tos']}\n"
                    out_string += f"Total Fouls: {member_data_dict['fouls']}\n"
                    found_member = True
                    break
            if found_member:
                stats_embed = discord.Embed(title=f"Baller Stats for **{target_member.display_name}** in **{guild.name}**", description=out_string)
            else:
                stats_embed = discord.Embed(title=f"Baller Stats for **{target_member.display_name}** in **{guild.name}**", description="No Baller 1v1 stats exists for this user in this server")
            await channel.send(embed=stats_embed)

    async def start_match(self, guild_id):
        if guild_id not in self.guild_games:
            return
        
        self.guild_games[guild_id]["game_started"] = True
        self.guild_games[guild_id]["cur_offense"] = self.guild_games[guild_id]["player1"]
        self.guild_games[guild_id]["cur_defense"] = self.guild_games[guild_id]["player2"]

        guild = self.guild_games[guild_id]["guild"]

        player_message_embed_str = f"Starting Baller 1v1 match!"
        player_message_embed = discord.Embed(title=f"Baller 1v1 Match in {guild.name}", description=player_message_embed_str)

        await self.guild_games[guild_id]["cur_offense"].send(embed=player_message_embed)
        await self.guild_games[guild_id]["cur_defense"].send(embed=player_message_embed)
        
        await self.next_stage(guild_id)
    
    async def next_stage(self, guild_id):
        guild_dict = self.guild_games[guild_id]
        guild = guild_dict["guild"]
        channel = guild_dict["channel"]
        p1_id = guild_dict["player1"].id
        p2_id = guild_dict["player2"].id
        p1_name = guild_dict['player1'].display_name
        p2_name = guild_dict['player2'].display_name
        cur_offense = guild_dict["cur_offense"]
        cur_defense = guild_dict["cur_defense"]
        offense_id = guild_dict["cur_offense"].id
        defense_id = guild_dict["cur_defense"].id
        offense_name = guild_dict["cur_offense"].display_name
        defense_name = guild_dict["cur_defense"].display_name
        # First stage
        if guild_dict["stage"] == 0:
            channel_message_embed_str = "It's " + guild_dict["cur_offense"].display_name + "'s turn on offense.\nThey are starting at the top of the key."
            channel_message_embed = discord.Embed(title=f"Baller 1v1 Match (**{p1_name}** vs **{p2_name}**)", description=channel_message_embed_str)
            
            offense_message_embed_str = "It is your turn on offense at the top of the key.\nType 'shoot' to shoot\nType 'cross' to drive"
            offense_message_embed = discord.Embed(title=f"Baller 1v1 Match ({p1_name} vs. {p2_name}) in {guild.name}", description=offense_message_embed_str)
            defense_message_embed_str = f"It is {guild_dict['cur_offense'].display_name}'s turn on offense at the top of the key.\nType 'block' to attempt to block the ball\nType 'steal' to attempt to steal the ball\n"
            defense_message_embed = discord.Embed(title=f"Baller 1v1 Match ({p1_name} vs. {p2_name}) in {guild.name}", description=defense_message_embed_str)
            
            await channel.send(embed=channel_message_embed)
            await guild_dict["cur_offense"].send(embed=offense_message_embed)
            await guild_dict["cur_defense"].send(embed=defense_message_embed)

            guild_dict["stage"] = 1
        else:
            # Return if both players haven't made their choice
            if guild_dict["offense_choice"] == -1 or guild_dict["defense_choice"] == -1:
                return
            
            # Reset game timer
            guild_dict["game_time_remaining"] = self.game_timeout_length
            
            offense_choice = guild_dict["offense_choice"]
            defense_choice = guild_dict["defense_choice"]
            if guild_dict["stage"] == 1:
                # Offense shoots 3; Defense blocks 3 (Defense gets ball)
                # Offense +1 3PA
                # Offense +1 FGA
                # Defense +1 Block
                if offense_choice == 0 and defense_choice == 0:
                    output = self.STAGE_1_OFFENSE_0_DEFENSE_0[random.randint(0, len(self.STAGE_1_OFFENSE_0_DEFENSE_0) - 1)].format(offense_name,defense_name)
                    self.add_stat(guild_id, offense_id, "3pas", 1)
                    self.add_stat(guild_id, offense_id, "fgas", 1)
                    self.add_stat(guild_id, defense_id, "blocks", 1)
                    await self.send_turn_message(guild_id, output)
                    await self.next_turn(guild_id, 1)
                # Offense shoots 3; Defense steals (Offense makes 3)
                # Offense +1 3PA
                # Offense +1 3PM
                # Offense +1 FGA
                # Offense +1 FGM
                # Offense +3 Point
                elif offense_choice == 0 and defense_choice == 1:
                    output = self.STAGE_1_OFFENSE_0_DEFENSE_1[random.randint(0, len(self.STAGE_1_OFFENSE_0_DEFENSE_1) - 1)].format(offense_name,defense_name)
                    await self.send_turn_message(guild_id, output)
                    if offense_id == p1_id:
                        guild_dict["player1_score"] += self.THREE_POINT_WEIGHT
                    elif offense_id == p2_id:
                        guild_dict["player2_score"] += self.THREE_POINT_WEIGHT
                    self.add_stat(guild_id, offense_id, "3pas", 1)
                    self.add_stat(guild_id, offense_id, "3pms", 1)
                    self.add_stat(guild_id, offense_id, "fgas", 1)
                    self.add_stat(guild_id, offense_id, "fgms", 1)
                    self.add_stat(guild_id, offense_id, "points", 3)
                    await self.next_turn(guild_id, 1)
                # Offense dribbles; Defense tries to block (Offense gets to point aka stage 2)
                # No stat change
                elif offense_choice == 1 and defense_choice == 0:
                    output = self.STAGE_1_OFFENSE_1_DEFENSE_0[random.randint(0, len(self.STAGE_1_OFFENSE_1_DEFENSE_0) - 1)].format(offense_name,defense_name)
                    await self.send_turn_message(guild_id, output)
                    guild_dict["stage"] = 2

                    channel_message = f"{offense_name} has made their way into the paint.\nWhat will the players do next?"
                    offense_message = f"You are now in the paint!\nType 'shoot' to attempt a shot\nType 'fake' to attempt a fake"
                    defense_message = f"{offense_name} is now in the paint!\nType 'block' to attempt a block\nType 'steal' to attempt a steal"

                    channel_message_embed = discord.Embed(title=f"Baller 1v1 Match in {guild.name}", description=channel_message)
                    offense_message_embed = discord.Embed(title=f"Baller 1v1 Match in {guild.name}", description=offense_message)
                    defense_message_embed = discord.Embed(title=f"Baller 1v1 Match in {guild.name}", description=defense_message)

                    await channel.send(embed=channel_message_embed)
                    await cur_offense.send(embed=offense_message_embed)
                    await cur_defense.send(embed=defense_message_embed)
                # Offense dribbles; Defense tries steals (Defense gets the ball)
                # Offense +1 TO
                # Defense +1 Steal
                elif offense_choice == 1 and defense_choice == 1:
                    output = self.STAGE_1_OFFENSE_1_DEFENSE_1[random.randint(0, len(self.STAGE_1_OFFENSE_1_DEFENSE_1) - 1)].format(offense_name,defense_name)
                    self.add_stat(guild_id, offense_id, "tos", 1)
                    self.add_stat(guild_id, defense_id, "steals", 1)
                    await self.send_turn_message(guild_id, output)
                    await self.next_turn(guild_id, 1)
            elif guild_dict["stage"] == 2:
                # Offense goes for dunk; Defense blocks dunk (Defense gets ball)
                # Offense +1 FGA
                # Defense +1 Block
                if offense_choice == 0 and defense_choice == 0:
                    output = self.STAGE_2_OFFENSE_0_DEFENSE_0[random.randint(0, len(self.STAGE_2_OFFENSE_0_DEFENSE_0) - 1)].format(offense_name,defense_name)
                    self.add_stat(guild_id, offense_id, "fgas", 1)
                    self.add_stat(guild_id, defense_id, "blocks", 1)
                    await self.send_turn_message(guild_id, output)
                    await self.next_turn(guild_id, 1)
                # Offense goes for dunk; Defense goes for steal (Offense gets and1 dunk)
                # Offense +1 FGA
                # Offense +1 FGM
                # Offense +1 And1
                # Offense +1 Dunk
                # Offense +2 Point
                # Defense +1 Foul
                elif offense_choice == 0 and defense_choice == 1:
                    output = self.STAGE_2_OFFENSE_0_DEFENSE_1[random.randint(0, len(self.STAGE_2_OFFENSE_0_DEFENSE_1) - 1)].format(offense_name,defense_name)
                    await self.send_turn_message(guild_id, output)
                    if offense_id == p1_id:
                        guild_dict["player1_score"] += self.TWO_POINT_WEIGHT
                    elif offense_id == p2_id:
                        guild_dict["player2_score"] += self.TWO_POINT_WEIGHT
                    self.add_stat(guild_id, offense_id, "fgas", 1)
                    self.add_stat(guild_id, offense_id, "fgms", 1)
                    self.add_stat(guild_id, offense_id, "and1s", 1)
                    self.add_stat(guild_id, offense_id, "dunks", 1)
                    self.add_stat(guild_id, offense_id, "points", 2)
                    self.add_stat(guild_id, defense_id, "fouls", 1)
                    await self.next_turn(guild_id, 0)
                # Offense goes for pump fake -> layup; Defense goes for block (Offense gets and1 layup)
                # Offense +1 FGA
                # Offense +1 FGM
                # Offense +1 And1
                # Offense +1 Layup
                # Offense +2 Point
                # Defense +1 Foul
                elif offense_choice == 1 and defense_choice == 0:
                    output = self.STAGE_2_OFFENSE_1_DEFENSE_0[random.randint(0, len(self.STAGE_2_OFFENSE_1_DEFENSE_0) - 1)].format(offense_name,defense_name)
                    await self.send_turn_message(guild_id, output)
                    if offense_id == p1_id:
                        guild_dict["player1_score"] += self.TWO_POINT_WEIGHT
                    elif offense_id == p2_id:
                        guild_dict["player2_score"] += self.TWO_POINT_WEIGHT
                    self.add_stat(guild_id, offense_id, "fgas", 1)
                    self.add_stat(guild_id, offense_id, "fgms", 1)
                    self.add_stat(guild_id, offense_id, "and1s", 1)
                    self.add_stat(guild_id, offense_id, "layups", 1)
                    self.add_stat(guild_id, offense_id, "points", 2)
                    self.add_stat(guild_id, defense_id, "fouls", 1)
                    await self.next_turn(guild_id, 0)
                # Offense goes for pump fake; Defense goes for steal (Defense gets steal)
                # Offense +1 TO
                # Defense +1 Steal
                elif offense_choice == 1 and defense_choice == 1:
                    output = self.STAGE_2_OFFENSE_1_DEFENSE_1[random.randint(0, len(self.STAGE_2_OFFENSE_1_DEFENSE_1) - 1)].format(offense_name,defense_name)
                    self.add_stat(guild_id, offense_id, "tos", 1)
                    self.add_stat(guild_id, defense_id, "steals", 1)
                    await self.send_turn_message(guild_id, output)
                    await self.next_turn(guild_id, 1)
            guild_dict["offense_choice"] = -1
            guild_dict["defense_choice"] = -1


    async def send_turn_message(self, guild_id, output):
        guild_dict = self.guild_games[guild_id]
        guild = guild_dict["guild"]
        channel = guild_dict["channel"]
        p1_name = guild_dict['player1'].display_name
        p2_name = guild_dict['player2'].display_name
        cur_offense = guild_dict["cur_offense"]
        cur_defense = guild_dict["cur_defense"]
        guild_message_title = f"Baller 1v1 Match (**{p1_name}** vs. **{p2_name}**)"
        player_message_title = f"Baller 1v1 Match (**{p1_name}** vs. **{p2_name}**) in **{guild.name}** server"

        guild_message_embed = discord.Embed(title=guild_message_title, description=output)
        player_messaged_embed = discord.Embed(title=player_message_title, description=output)
        
        await channel.send(embed=guild_message_embed)
        await cur_offense.send(embed=player_messaged_embed)
        await cur_defense.send(embed=player_messaged_embed)

    async def next_turn(self, guild_id, stay_or_switch):
        guild_dict = self.guild_games[guild_id]
        guild_name = guild_dict["guild"].name
        channel = guild_dict["channel"]
        p1 = guild_dict["player1"]
        p2 = guild_dict["player2"]
        p1_name = guild_dict["player1"].display_name
        p2_name = guild_dict["player2"].display_name
        p1_score = guild_dict["player1_score"]
        p2_score = guild_dict["player2_score"]

        if p1_score >= guild_dict["target_score"] or p2_score >= guild_dict["target_score"]:
            channel_embed_title = f"BALLER 1v1 GAME OVER!\n\nThe final score was:\n{p1_name}: {p1_score} - {p2_name}: {p2_score}\n"
            player_embed_title = f"BALLER 1v1 in {guild_name} GAME OVER!\n\nThe final score was:\n{p1_name}: {p1_score} - {p2_name}: {p2_score}\n"
            channel_message = ""
            p1_message = ""
            p2_message = ""

            if p1_score >= guild_dict["target_score"]:
                channel_message = f"{p1_name} wins!!!"
                p1_message = "Congratulations!"
                p2_message = "Better luck next time!"
                self.add_stat(guild_id, p1.id, "wins", 1)
                self.add_stat(guild_id, p2.id, "losses", 1)
            if p2_score >= guild_dict["target_score"]:
                channel_message = f"{p2_name} wins!!!"
                p1_message = "Better luck next time!"
                p2_message = "Congratulations!"
                self.add_stat(guild_id, p2.id, "wins", 1)
                self.add_stat(guild_id, p1.id, "losses", 1)
            self.add_stat(guild_id, p1.id, "games_played", 1)
            self.add_stat(guild_id, p2.id, "games_played", 1)

            channel_embed = discord.embeds.Embed(title=channel_embed_title, description=channel_message)
            p1_embed = discord.embeds.Embed(title=player_embed_title, description=p1_message)
            p2_embed = discord.embeds.Embed(title=player_embed_title, description=p2_message)
            await channel.send(embed=channel_embed)
            await p1.send(embed=p1_embed)
            await p2.send(embed=p2_embed)

            self.end_game(guild_id)
            return
        # Switch offense and defense
        if stay_or_switch == 1:
            guild_dict["cur_offense"], guild_dict["cur_defense"] = guild_dict["cur_defense"], guild_dict["cur_offense"]
        # Reset stage to 0
        guild_dict["stage"] = 0

        turn_message = f"The score is now {p1_name}: {p1_score} - {p2_name}: {p2_score}"
        channel_turn_embed = discord.embeds.Embed(title=f"Baller 1v1 Match ({p1_name} vs. {p2_name})", description=turn_message)
        player_turn_embed = discord.embeds.Embed(title=f"Baller 1v1 Match ({p1_name} vs. {p2_name}) in {guild_name}", description=turn_message)
        await channel.send(embed=channel_turn_embed)
        await p1.send(embed=player_turn_embed)
        await p2.send(embed=player_turn_embed)
        await self.next_stage(guild_id)

    def reset_game(self, guild_id, guild=None, channel=None, player1_member=None, player2_member=None, target_score=-1):
        self.guild_games[guild_id] =    {
                                            "guild": guild,
                                            "channel" : channel,
                                            "player1": player1_member,
                                            "player2": player2_member,
                                            "target_score": target_score,
                                            "game_started": False,
                                            "cur_offense": None,
                                            "cur_defense": None,
                                            "offense_choice": -1,
                                            "defense_choice": -1,
                                            "player1_score": 0,
                                            "player2_score": 0,
                                            "stage": 0,
                                            "accept_time_remaining" : self.accept_timeout_length,
                                            "game_time_remaining" : self.game_timeout_length,
                                            "final_stats": {
                                                player1_member.id : dict(self.DEFAULT_BALLER_DATA),
                                                player2_member.id: dict(self.DEFAULT_BALLER_DATA)
                                            }
                                        }
    def end_game(self, guild_id):
        self.write_final_stats(guild_id)
        del self.guild_games[guild_id]

    @tasks.loop(seconds=1.0)
    async def game_loop(self):
        # Loop through active guild games
        if len(self.guild_games) > 0:
            end_list = []           # List of games to end because time out
            unaccept_list = []      # List of games to end because never accepted
            for g in self.guild_games:
                # If game hasn't started, decrement accept time remaining
                if self.guild_games[g]["game_started"] == False:
                    self.guild_games[g]["accept_time_remaining"] -= 1
                    # Add server to unaccept list if run out of accept time
                    if self.guild_games[g]["accept_time_remaining"] <= 0:
                        unaccept_list.append(g)
                # Decrement game_time_remaining and add server to end_list if run out of game time
                self.guild_games[g]["game_time_remaining"] -= 1
                if self.guild_games[g]["game_time_remaining"] <= 0:
                    end_list.append(g)
            # End all games in end list and notify player and channel
            for e in end_list:
                guild_dict = self.guild_games[e]
                channel = guild_dict["channel"]
                guild = guild_dict["guild"]
                p1 = guild_dict['player1']
                p2 = guild_dict['player2']
                p1_name = guild_dict['player1'].display_name
                p2_name = guild_dict['player2'].display_name
                p1_score = guild_dict['player1_score']
                p2_score = guild_dict['player2_score']
                cur_offense = guild_dict["cur_offense"]
                cur_defense = guild_dict["cur_defense"]
                offense_choice = guild_dict["offense_choice"]
                defense_choice = guild_dict["defense_choice"]

                # If one player made a choice and the other didn't, treat is as if the second player for
                # Offense chose but defense didn't
                if offense_choice != -1 and defense_choice == -1:
                    # Player 1 forfeits
                    if p1.id == cur_defense.id:
                        end_game_embed = discord.embeds.Embed(title=f"**{p1_name}** vs **{p2_name}** Baller 1v1 Match in **{guild.name}** was ended!",
                                                            description=f"**{p1_name}** foreited the match by not making a move in time!")
                        await guild_dict["channel"].send(embed=end_game_embed)
                        await guild_dict["player1"].send(embed=end_game_embed)
                        await guild_dict["player2"].send(embed=end_game_embed)
                        self.add_stat(e, p1.id, "forfeits", 1)
                        self.add_stat(e, p1.id, "losses", 1)
                        self.add_stat(e, p2.id, "wins", 1)
                    # Player 2 forfeits
                    elif p2.id == cur_defense.id:
                        end_game_embed = discord.embeds.Embed(title=f"**{p1_name}** vs **{p2_name}** Baller 1v1 Match in **{guild.name}** was ended!",
                                                            description=f"**{p2_name}** foreited the match by not making a move in time!")
                        await guild_dict["channel"].send(embed=end_game_embed)
                        await guild_dict["player1"].send(embed=end_game_embed)
                        await guild_dict["player2"].send(embed=end_game_embed)
                        self.add_stat(e, p2.id, "forfeits", 1)
                        self.add_stat(e, p2.id, "losses", 1)
                        self.add_stat(e, p1.id, "wins", 1)
                # Defense chose but offense didn't
                elif offense_choice == -1 and defense_choice != -1:
                    # Player 1 forfeits
                    if p1.id == cur_offense.id:
                        end_game_embed = discord.embeds.Embed(title=f"**{p1_name}** vs **{p2_name}** Baller 1v1 Match in **{guild.name}** was ended!",
                                                            description=f"**{p1_name}** foreited the match by not making a move in time!")
                        await guild_dict["channel"].send(embed=end_game_embed)
                        await guild_dict["player1"].send(embed=end_game_embed)
                        await guild_dict["player2"].send(embed=end_game_embed)
                        self.add_stat(e, p1.id, "forfeits", 1)
                        self.add_stat(e, p1.id, "losses", 1)
                        self.add_stat(e, p2.id, "wins", 1)
                    # Player 2 forfeits
                    elif p2.id == cur_offense.id:
                        end_game_embed = discord.embeds.Embed(title=f"**{p1_name}** vs **{p2_name}** Baller 1v1 Match in **{guild.name}** was ended!",
                                                            description=f"**{p2_name}** foreited the match by not making a move in time!")
                        await guild_dict["channel"].send(embed=end_game_embed)
                        await guild_dict["player1"].send(embed=end_game_embed)
                        await guild_dict["player2"].send(embed=end_game_embed)
                        self.add_stat(e, p2.id, "forfeits", 1)
                        self.add_stat(e, p2.id, "losses", 1)
                        self.add_stat(e, p1.id, "wins", 1)
                # Both players did not choose in time
                elif offense_choice == -1 and defense_choice == -1:
                    message_embed_str = f"{self.game_timeout_length} seconds passed without both players making a move. Ending match!\nThe score was **__{p1.display_name}: {p1_score}__** - **__{p2.display_name}: {p2_score}__**"
                    player_message_embed = discord.Embed(title=f"Baller 1v1 Match ({p1_name} vs. {p2_name}) in {guild.name}", description=message_embed_str)
                    channel_message_embed = discord.Embed(title=f"Baller 1v1 Match ({p1_name} vs. {p2_name})", description=message_embed_str)
                    await channel.send(embed=channel_message_embed)
                    await p1.send(embed=player_message_embed)
                    await p2.send(embed=player_message_embed)
                
                self.add_stat(e, p1.id, "games_played", 1)
                self.add_stat(e, p2.id, "games_played", 1)
                self.end_game(e)
            # End all games in unaccept list and notify channel
            for u in unaccept_list:
                channel = self.guild_games[u]["channel"]
                await channel.send(f"The match was not accepted in time. Ending match...")
                self.end_game(u)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        msg = message.content.upper()
        channel = message.channel
        member = message.author

        # Ignore bot messages
        if member.bot:
            return

        if isinstance(channel, discord.channel.TextChannel):
            guild = message.guild
            # Only check messages if baller match exists in the server
            if guild.id not in self.guild_games:
                return
            guild_dict = self.guild_games[guild.id]
            if guild_dict["game_started"] == False:
                # Don't check the message if it's not from the challengee
                if member.id != guild_dict["player2"].id:
                    return
                # Start match if challengee types "a" or "A"
                if msg == "a" or msg == "A":
                    await channel.send(f"{member.display_name} has accepted the match!")
                    p1 = guild_dict['player1']
                    p2 = guild_dict['player2']
                    match_embed = discord.Embed(title=f"**Starting Baller 1v1 Match between {p1.display_name} and {p2.display_name}**\n", description="Please check your DMs to continue playing the match.")
                    await channel.send(embed=match_embed)
                    guild_dict["game_started"] = True
                    await self.start_match(guild.id)
                elif msg == "d" or msg == "D":
                    await channel.send(f"{member.display_name} has declined the match!")
                    self.end_game(guild.id)
        elif isinstance(channel, discord.channel.DMChannel):
            target_guild_id = -1
            # Find server in which the player's current game is in
            for guild_id in self.guild_games:
                if self.guild_games[guild_id]["cur_offense"] == None:
                    continue
                if self.guild_games[guild_id]["cur_offense"].id == member.id or self.guild_games[guild_id]["cur_defense"].id == member.id:
                    target_guild_id = guild_id
            # Return if couldn't find server
            if target_guild_id < 0:
                return
            # Return if match hasn't started yet
            if self.guild_games[target_guild_id]["game_started"] == False:
                return
            
            guild_dict = self.guild_games[target_guild_id]
            # Handle user forfeiting the match
            if msg.lower() == "stop" or msg.lower() == "forfeit":
                player1_name = guild_dict["player1"].display_name
                player2_name = guild_dict["player2"].display_name
                guild_name = guild_dict["guild"].name

                end_game_embed = discord.embeds.Embed(title=f"**{player1_name}** vs **{player2_name}** Baller 1v1 Match in **{guild_name}** was ended!",
                                                      description=f"**{member.display_name}** foreited the match!")
                await guild_dict["channel"].send(embed=end_game_embed)
                await guild_dict["player1"].send(embed=end_game_embed)
                await guild_dict["player2"].send(embed=end_game_embed)

                self.add_stat(target_guild_id, member.id, "forfeits", 1)
                self.add_stat(target_guild_id, member.id, "losses", 1)
                self.add_stat(target_guild_id, member.id, "games_played", 1)

                other_player_id = guild_dict["player1"].id
                if guild_dict["player1"].id == member.id:
                    other_player_id = guild_dict["player2"].id
                self.add_stat(target_guild_id, other_player_id, "wins", 1)
                self.add_stat(target_guild_id, other_player_id, "games_played", 1)

                self.end_game(guild_id)
                return

            cur_stage = guild_dict["stage"]
            cur_offense_id = guild_dict["cur_offense"].id
            cur_defense_id = guild_dict["cur_defense"].id

            offense_options = []
            defense_options = []
            # Return if game hasn't started yet
            if cur_stage == 0:
                return
            # At the top of the key
            elif cur_stage == 1:
                offense_options = ["shoot", "cross"]
                defense_options = ["block", "steal"]
                # Ignore messages that aren't in the listed options
                if msg.lower() not in offense_options and msg.lower() not in defense_options:
                    return
            # In the paint
            elif cur_stage == 2:
                offense_options = ["shoot", "fake"]
                defense_options = ["block", "steal"]
                # Ignore messages that aren't in the listed options
                if msg.lower() not in offense_options and msg.lower() not in defense_options:
                    return
                
            # Message sender is the offense player
            if member.id == cur_offense_id:
                # Ignore if member message isn't part of offense player's options
                if msg.lower() not in offense_options:
                    return
                # Set offense's choice
                if msg.lower() == offense_options[0]:
                    self.guild_games[target_guild_id]["offense_choice"] = 0
                elif msg.lower() == offense_options[1]:
                    self.guild_games[target_guild_id]["offense_choice"] = 1
                await self.next_stage(guild_id)
            # Message sender is the defense player
            elif member.id == cur_defense_id:
                # Ignore if member message isn't part of defense player's options
                if msg.lower() not in defense_options:
                    return
                # Set defense's choice
                if msg.lower() == defense_options[0]:
                    self.guild_games[target_guild_id]["defense_choice"] = 0
                elif msg.lower() == defense_options[1]:
                    self.guild_games[target_guild_id]["defense_choice"] = 1
                await self.next_stage(guild_id)

    def add_stat(self, guild_id, member_id, stat, amount_to_add):
        guild_dict = self.guild_games[guild_id]
        # Skip if member not one of the two players
        if member_id not in guild_dict["final_stats"]:
            return
        # Skip if the stat being added doesn't exist
        if stat not in guild_dict["final_stats"][member_id]:
            return
        guild_dict["final_stats"][member_id][stat] += amount_to_add

    # Add final stats to the player's stats
    # 'stat' can be: games_played|wins|losses|forfeits|points|threes|and1s|dunks|layups|blocks|steals
    def write_final_stats(self, guild_id):
        guild_dict = self.guild_games[guild_id]
        str_guild_id = str(guild_id)
        guilds_data_dict = {}
        with open(self.bot.data_file, 'r') as f:
            guilds_data_dict = json.load(f)
            # Loop through the two player ids in the final_stats dict
            for member_id in list(guild_dict["final_stats"].keys()):
                str_member_id = str(member_id)
                # Check if member id exists in the data file
                if str_member_id in guilds_data_dict[str_guild_id]["baller_data"]:
                    # Loop through all stats in the final_stats dict
                    for stat in guild_dict["final_stats"][member_id]:
                        # Add the final_stats value for that stat to the player's data if it exists or set it if it doesn't exist
                        if stat in guilds_data_dict[str_guild_id]["baller_data"][str_member_id]:
                            guilds_data_dict[str_guild_id]["baller_data"][str_member_id][stat] += guild_dict["final_stats"][member_id][stat]
                        else:
                            guilds_data_dict[str_guild_id]["baller_data"][str_member_id][stat] = guild_dict["final_stats"][member_id][stat]
                # Create new member entry in data file if the member's id didn't already exist
                else:
                    guilds_data_dict[str_guild_id]["baller_data"][str_member_id] = dict(self.DEFAULT_BALLER_DATA)
                    # Loop through all stats in the final_stats dict
                    for stat in guild_dict["final_stats"][member_id]:
                        # Add the final_stats value for that stat to the player's data if it exists or set it if it doesn't exist
                        if stat in guilds_data_dict[str_guild_id]["baller_data"][str_member_id]:
                            guilds_data_dict[str_guild_id]["baller_data"][str_member_id][stat] += guild_dict["final_stats"][member_id][stat]
                        else:
                            guilds_data_dict[str_guild_id]["baller_data"][str_member_id][stat] = guild_dict["final_stats"][member_id][stat]
        with open(self.bot.data_file, 'w', encoding='utf-8') as f:
            json.dump(guilds_data_dict, f, ensure_ascii=False, indent=4)

async def setup(bot):
    await bot.add_cog(Baller(bot))
    print(f'Baller Cog is being loaded')

def teardown(bot):
    print(f'Baller Cog is being removed')
