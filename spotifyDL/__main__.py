from pyfiglet import Figlet
from .ytmusic_tools import ytmusic_tools
from simple_chalk import chalk
import click

@click.command()
@click.option('--url', '-u', prompt='please enter a spotify url',
              help='The url of the track song or playlist you want to download')
def main(url):
    ytmusic = ytmusic_tools()
    f = Figlet()
    print(chalk.magentaBright(f.renderText('Spotify-DL')))
    ytmusic.download(url)
    print(chalk.magentaBright('finished!'))


if __name__ == '__main__':
    main()
